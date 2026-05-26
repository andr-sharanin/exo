"""
Kernel Filter Service — analyzes every new task against the user's kernels.

Flow:
    1. Load active PolicyKernel (behavioral) + StrategicKernel (goals)
    2. Ask AI: does this task align with who you are and what you're pursuing?
    3. Return recommendation + alignment score + conflicts
    4. API sets command status to "pending_confirmation" if confirm_required=True
    5. User confirms or declines → task proceeds or gets deferred
"""
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy_kernel import PolicyKernel
from app.models.strategic_kernel import StrategicKernel
from app.services.ai_client import AIClient


class KernelAnalysis:
    def __init__(self, data: dict):
        self.alignment_score: int = data.get("alignment_score", 50)
        self.recommendation: str = data.get("recommendation", "neutral")
        self.reasoning: str = data.get("reasoning", "")
        self.conflicts: list[str] = data.get("conflicts", [])
        self.synergies: list[str] = data.get("synergies", [])
        self.confirm_required: bool = data.get("confirm_required", False)
        self.suggested_timing: str | None = data.get("suggested_timing")
        self.defer_reason: str | None = data.get("defer_reason")

    def to_dict(self) -> dict:
        return {
            "alignment_score": self.alignment_score,
            "recommendation": self.recommendation,
            "reasoning": self.reasoning,
            "conflicts": self.conflicts,
            "synergies": self.synergies,
            "confirm_required": self.confirm_required,
            "suggested_timing": self.suggested_timing,
            "defer_reason": self.defer_reason,
        }


class KernelFilterService:
    """
    Analyzes tasks through policy + strategic kernels.
    Requires AI call (Tier 2 — Analytical).
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai = AIClient(db)

    async def analyze(
        self,
        user_id: str,
        tenant_id: str,
        task_raw_input: str,
        task_context: dict | None = None,
    ) -> KernelAnalysis:
        """
        Analyze a task against the user's active kernels.
        Returns KernelAnalysis with recommendation and alignment score.
        """
        policy = await self._get_active_policy_kernel(user_id)
        strategic = await self._get_active_strategic_kernel(user_id)

        if policy is None and strategic is None:
            # No kernels yet — onboarding not completed, skip analysis
            return KernelAnalysis({
                "alignment_score": 70,
                "recommendation": "proceed",
                "reasoning": "No kernels formed yet. Complete onboarding for personalized analysis.",
                "confirm_required": False,
            })

        prompt = self._build_prompt(task_raw_input, task_context, policy, strategic)

        try:
            raw = await self.ai.complete(
                system=_SYSTEM_PROMPT,
                user=prompt,
                tier=2,
            )
            data = json.loads(raw)
        except Exception:
            # AI failure → let the task through, don't block the user
            return KernelAnalysis({
                "alignment_score": 50,
                "recommendation": "proceed",
                "reasoning": "Analysis temporarily unavailable.",
                "confirm_required": False,
            })

        return KernelAnalysis(data)

    async def _get_active_policy_kernel(self, user_id: str) -> PolicyKernel | None:
        q = (
            select(PolicyKernel)
            .where(
                PolicyKernel.user_id == user_id,
                PolicyKernel.is_active == True,  # noqa: E712
            )
            .order_by(PolicyKernel.version.desc())
            .limit(1)
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def _get_active_strategic_kernel(self, user_id: str) -> StrategicKernel | None:
        q = (
            select(StrategicKernel)
            .where(
                StrategicKernel.user_id == user_id,
                StrategicKernel.is_active == True,  # noqa: E712
            )
            .order_by(StrategicKernel.version.desc())
            .limit(1)
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    def _build_prompt(
        self,
        task: str,
        context: dict | None,
        policy: PolicyKernel | None,
        strategic: StrategicKernel | None,
    ) -> str:
        sections = [f"NEW TASK: {task}"]

        if context:
            sections.append(f"TASK CONTEXT: {json.dumps(context, ensure_ascii=False)}")

        if policy:
            sections.append(f"""
BEHAVIORAL KERNEL (how this user works):
- Focus stability: {policy.focus_stability}
- Task handling: {policy.task_handling_style}
- Decision style: {policy.decision_style}
- Dominant mode: {policy.dominant_mode}
- Execution pattern: {policy.execution_pattern}
- Overload threshold: {policy.overload_threshold}
- Constraints: {json.dumps(policy.constraints or [], ensure_ascii=False)}
- Strengths: {json.dumps(policy.strengths or [], ensure_ascii=False)}
""")

        if strategic:
            sections.append(f"""
STRATEGIC KERNEL (what this user is pursuing NOW):
{strategic.strategic_context_for_ai or ""}
- Vision: {strategic.vision_summary}
- Weekly focus: {json.dumps(strategic.weekly_focus or [], ensure_ascii=False)}
- NOT NOW list: {json.dumps(strategic.not_now or [], ensure_ascii=False)}
""")

        return "\n".join(sections)


_SYSTEM_PROMPT = """You are an executive advisor analyzing whether a task aligns with the user's behavioral profile and strategic goals.

Be direct and honest. Your job is to protect the user's time and focus.

Respond ONLY in valid JSON with this exact structure:
{
  "alignment_score": <0-100, how well task aligns with kernels>,
  "recommendation": <"proceed"|"defer"|"decline"|"neutral">,
  "reasoning": "<1-2 sentences explaining why>",
  "conflicts": ["<conflict with kernel 1>", ...],
  "synergies": ["<how this helps goal X>", ...],
  "confirm_required": <true if score < 40 or recommendation is defer/decline>,
  "suggested_timing": "<null or 'next_week'|'next_month'|'someday'>",
  "defer_reason": "<null or reason why deferral makes sense>"
}

Rules:
- alignment_score >= 70: proceed without confirmation
- alignment_score 40-69: neutral, user may confirm
- alignment_score < 40: confirm_required = true
- If task is on NOT NOW list or conflicts with weekly_focus: recommend defer, confirm_required = true
- If user is in recovery/crisis mode and task is non-critical: recommend defer
- Respond in the same language as the task text"""
