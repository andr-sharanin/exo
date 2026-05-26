"""
BehavioralPolicyEngine — impulse interruption and event response protocol.

Pure stateless class methods. Evaluates a behavioural event type and returns the
appropriate policy response. Energy state modulates response intensity.
"""
from dataclasses import dataclass, field
from enum import StrEnum

from app.services.energy import EnergyState


class PolicyAction(StrEnum):
    INTERRUPT = "interrupt"      # urge_event: mandatory pause before acting
    ACKNOWLEDGE = "acknowledge"  # lapse_event: compassionate recognition
    REINFORCE = "reinforce"      # recovery_event: positive reinforcement
    ALERT = "alert"              # risk_window: proactive protective alert


@dataclass
class PolicyResponse:
    action: PolicyAction
    delay_minutes: int
    reflection_prompt: str
    alternative_suggestions: list[str] = field(default_factory=list)


class BehavioralPolicyEngine:
    """
    Stateless engine. Call evaluate() with event type and current energy state.
    Energy state modulates the interrupt delay: depleted willpower needs longer pauses.
    """

    @classmethod
    def evaluate(cls, event_type: str, *, energy_state: EnergyState) -> PolicyResponse:
        if event_type == "urge_event":
            # Critical energy → longer pause (depleted willpower, higher relapse risk)
            delay = 15 if energy_state == EnergyState.CRITICAL else 10
            return PolicyResponse(
                action=PolicyAction.INTERRUPT,
                delay_minutes=delay,
                reflection_prompt=(
                    "Pause. Before acting, ask: what need is this urge trying to meet? "
                    "You have committed to a different path."
                ),
                alternative_suggestions=[
                    "Take a 10-minute walk",
                    "Call or message someone in your support network",
                    "Review your commitments and why they matter to you",
                ],
            )

        if event_type == "lapse_event":
            return PolicyResponse(
                action=PolicyAction.ACKNOWLEDGE,
                delay_minutes=0,
                reflection_prompt=(
                    "A lapse is information, not failure. "
                    "What can you learn from this moment? Recovery begins now."
                ),
                alternative_suggestions=[
                    "Write down what triggered this",
                    "Reach out to your support network",
                    "Recommit with one small, concrete next action",
                ],
            )

        if event_type == "recovery_event":
            return PolicyResponse(
                action=PolicyAction.REINFORCE,
                delay_minutes=0,
                reflection_prompt=(
                    "You chose your commitments over the impulse. "
                    "Each recovery builds capacity."
                ),
                alternative_suggestions=[],
            )

        # risk_window (and any unrecognised type defaults to alert)
        return PolicyResponse(
            action=PolicyAction.ALERT,
            delay_minutes=0,
            reflection_prompt=(
                "Pattern data suggests elevated risk right now. "
                "Consider protective actions before continuing."
            ),
            alternative_suggestions=[
                "Switch to Recovery mode temporarily",
                "Reduce today's schedule load",
                "Activate an accountability check-in",
            ],
        )
