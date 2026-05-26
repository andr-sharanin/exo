"""Background task: analyze command through policy + strategic kernels."""
import uuid


async def analyze_command_task(
    ctx: dict, command_id: str, user_id: str, tenant_id: str, raw_input: str
) -> dict:
    """
    ARQ task: run KernelFilterService on a new command.
    Updates command.kernel_status and creates task_analyses record.
    Publishes SSE 'task_analyzed' event so dashboard can update.
    """
    from app.core.database import AsyncSessionLocal
    from app.services.kernel_filter import KernelFilterService
    from app.services.event_publisher import publish
    from sqlalchemy import select, update
    from app.models.command import Command

    async with AsyncSessionLocal() as db:
        try:
            svc = KernelFilterService(db)
            analysis = await svc.analyze(
                user_id=user_id,
                tenant_id=tenant_id,
                task_raw_input=raw_input,
            )

            # Store analysis
            from app.models.task_analysis import TaskAnalysis
            from datetime import datetime, timezone
            ta = TaskAnalysis(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID(tenant_id),
                user_id=uuid.UUID(user_id),
                command_id=uuid.UUID(command_id),
                alignment_score=analysis.alignment_score,
                recommendation=analysis.recommendation,
                reasoning=analysis.reasoning,
                conflicts=analysis.conflicts,
                synergies=analysis.synergies,
                confirm_required=analysis.confirm_required,
                suggested_timing=analysis.suggested_timing,
                defer_reason=analysis.defer_reason,
            )
            db.add(ta)

            # Update command kernel_status
            new_status = (
                "pending_confirmation" if analysis.confirm_required else "confirmed"
            )
            await db.execute(
                update(Command)
                .where(Command.id == command_id)
                .values(kernel_status=new_status)
            )
            await db.commit()

            # Notify frontend via SSE
            await publish(user_id, "task_analyzed", {
                "command_id": command_id,
                "kernel_status": new_status,
                "alignment_score": analysis.alignment_score,
                "recommendation": analysis.recommendation,
                "confirm_required": analysis.confirm_required,
            })

            return {
                "command_id": command_id,
                "kernel_status": new_status,
                "alignment_score": analysis.alignment_score,
            }

        except Exception as exc:
            await publish(user_id, "job_failed", {
                "job": "analyze_command",
                "command_id": command_id,
                "error": str(exc),
            })
            raise
