# ADR-001: Rollback Strategy for ExoCortex Pipeline

**Status:** Accepted  
**Date:** 2026-04-30  
**Deciders:** Solo developer  

## Context

ExoCortex is built in sequential phases (0→12). Each phase delivers a vertical slice that must remain stable as subsequent phases are built on top. We need a clear, lightweight rollback strategy that a solo developer can actually execute without ceremony.

## Decision

### Layer 1 — Code: Git Tags at Phase DoD

Every phase is tagged at its Definition of Done:

```
git tag phase-0-done
git tag phase-1-done
git tag phase-2-done
# etc.
```

Rolling back to a prior phase:
```
git checkout phase-N-done
```

No branches — tags are immutable anchors. The main branch always reflects the latest completed phase.

### Layer 2 — Database: Alembic Downgrade Chain

Every migration in `alembic/versions/` has a tested `downgrade()` function. Rolling back the DB to phase N:

```bash
# Inside Docker
docker compose exec api alembic downgrade <revision_id>

# Or step by step
docker compose exec api alembic downgrade -1   # one step
docker compose exec api alembic downgrade base  # full reset
```

**Rule:** A migration without a working `downgrade()` is not accepted. CI verifies this by running `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` on every push.

### Layer 3 — Data: Postgres Backup Before Each Phase

Before starting a new phase on an environment with real data:

```bash
docker compose exec postgres pg_dump -U exocortex exocortex > backup_phase_N_$(date +%Y%m%d).sql
```

Restore:
```bash
docker compose exec -T postgres psql -U exocortex exocortex < backup_phase_N_YYYYMMDD.sql
```

### Layer 4 — Infrastructure: Docker Compose Pinned Images

All Docker images use explicit version tags (never `latest`). Rolling back infrastructure means reverting `docker-compose.yml` to the prior git tag and running `docker compose up -d`.

## Rollback Decision Matrix

| Scenario | Action |
|---|---|
| Bug in current phase, no data loss risk | Fix forward — patch and re-tag |
| Architectural mistake discovered mid-phase | `git checkout phase-N-done`, redesign |
| Migration broke production data | Restore pg_dump backup + `alembic downgrade` |
| Phase N broke phase N-1 contracts | `alembic downgrade` to N-1 revision, `git checkout phase-(N-1)-done` |
| Infrastructure config broken | Revert `docker-compose.yml` via git, `docker compose up -d` |

## "Fix Forward" Preference

Rollback is the last resort. The preferred path for bugs found during phase testing:

1. Write a failing test that reproduces the bug
2. Fix the bug in the current phase branch
3. Run full test suite
4. Re-tag if it was a DoD regression

Rollback is triggered only when the fix would require changing contracts established in previous phases.

## Solo Developer Governance (ADR mode)

In solo mode there is no Architecture Board. Instead, any decision to roll back a completed phase must be recorded as a new ADR entry explaining:
- What assumption was violated
- Why fix-forward is not viable
- What the rollback restores

This prevents silent rollbacks that erase context about why something was built a certain way.

## Consequences

**Positive:**
- Zero ceremony — git tags + alembic are already in the stack
- Rollback is deterministic and testable
- No external tools required (no Kubernetes, no blue-green, no feature flags at this stage)

**Negative:**
- No automated rollback trigger — developer must manually detect and execute
- pg_dump backups must be created manually before each phase (not automated yet)
- Phase tags must be applied consistently or the anchor is lost

## Phase Tag Reference

| Tag | Phase | Key Migrations |
|---|---|---|
| `phase-0-done` | Infrastructure + CI | — |
| `phase-1-done` | Kernel Data Contract | `0001_kernel_data_contract` |
| `phase-2-done` | Core Pipeline API | `0001_kernel_data_contract` |
| `phase-3-done` | Vertical Slice Validation | `0001_kernel_data_contract` |
