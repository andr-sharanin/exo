"""
OnboardingService — Kernel Calibration (Phase 5).

Pure stateless class methods. No database I/O.

Two modes:
  Quick (7 questions, ~10 min): covers 8 behavioural dimensions.
  Deep  (12 questions, ~45 min): adds failure_response_pattern + deeper signals.

Profile dimensions (stored in ClientKernelProfile.profile_data):
  focus_stability, task_handling_style, decision_style, overload_threshold,
  interruption_behavior, clarity_strategy, execution_pattern,
  help_seeking_behavior, failure_response_pattern

Computed defaults (stored in ClientKernelProfile.computed_defaults):
  dominant_mode, energy_archetype, recommended_session_length
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class OnboardingMode(StrEnum):
    QUICK = "quick"
    DEEP = "deep"


@dataclass
class QuestionOption:
    option_id: str
    text: str
    scores: dict[str, str]  # dimension → value


@dataclass
class OnboardingQuestion:
    question_id: str
    scenario: str
    options: list[QuestionOption]
    # "quick" = included in both modes; "deep" = deep mode only
    mode: Literal["quick", "deep"]


# ── Canonical question bank ────────────────────────────────────────────────────
# Order matters: score_answers() processes in canonical order so later (deep)
# questions overwrite earlier (quick) answers for the same dimension.

_QUESTIONS: list[OnboardingQuestion] = [
    # ── Quick (7 questions) ───────────────────────────────────────────────────
    OnboardingQuestion(
        question_id="Q_FOCUS",
        scenario=(
            "You're deep in a complex task. Three notifications pop up in a row."
        ),
        options=[
            QuestionOption("A", "Keep working — I check notifications only when I decide to", {"focus_stability": "high"}),
            QuestionOption("B", "Peek at one quickly, then refocus", {"focus_stability": "medium"}),
            QuestionOption("C", "End up checking all three before getting back", {"focus_stability": "low"}),
        ],
        mode="quick",
    ),
    OnboardingQuestion(
        question_id="Q_TASKS",
        scenario=(
            "It's Monday morning. You have 5 meaningful tasks to complete today."
        ),
        options=[
            QuestionOption("A", "Start task 1, finish it completely, then move to task 2", {"task_handling_style": "sequential"}),
            QuestionOption("B", "Work on all five in rotation throughout the day", {"task_handling_style": "parallel"}),
            QuestionOption("C", "Depends on what's happening around me", {"task_handling_style": "context_driven"}),
        ],
        mode="quick",
    ),
    OnboardingQuestion(
        question_id="Q_DECISION",
        scenario=(
            "You need to ship a feature today but realize there are two valid approaches."
        ),
        options=[
            QuestionOption("A", "Pick the first reasonable one and go — iterate if wrong", {"decision_style": "fast"}),
            QuestionOption("B", "Analyse both, research, then decide once confident", {"decision_style": "deliberate"}),
            QuestionOption("C", "Leave the decision for later, work on something else first", {"decision_style": "avoidant"}),
        ],
        mode="quick",
    ),
    OnboardingQuestion(
        question_id="Q_OVERLOAD",
        scenario=(
            "Your task list triples in size before noon. All items feel urgent."
        ),
        options=[
            QuestionOption("A", "I get sharper — I thrive under high load", {"overload_threshold": "high"}),
            QuestionOption("B", "Stressed, but I triage hard and execute the top 3", {"overload_threshold": "medium"}),
            QuestionOption("C", "I lock up and struggle to know where to start", {"overload_threshold": "low"}),
        ],
        mode="quick",
    ),
    OnboardingQuestion(
        question_id="Q_INTERRUPTION",
        scenario=(
            "A colleague interrupts your deep work with a question."
        ),
        options=[
            QuestionOption("A", "Help them, then jump back in — context stays warm", {"interruption_behavior": "adaptive"}),
            QuestionOption("B", "Hold up my hand, finish my sentence, then fully attend to them", {"interruption_behavior": "resistant"}),
            QuestionOption("C", "Help gladly, but take 10–15 min to rebuild focus after", {"interruption_behavior": "breaks"}),
        ],
        mode="quick",
    ),
    OnboardingQuestion(
        question_id="Q_EXECUTION",
        scenario=(
            "Given a free unstructured day, how do you naturally work best?"
        ),
        options=[
            QuestionOption("A", "Hard sprint for 2–3 hours, then need serious recovery", {"execution_pattern": "sprint"}),
            QuestionOption("B", "Steady 4–6 hours at a moderate, sustainable pace", {"execution_pattern": "marathon"}),
            QuestionOption("C", "30–45 minute focused bursts with short breaks between", {"execution_pattern": "burst"}),
        ],
        mode="quick",
    ),
    OnboardingQuestion(
        question_id="Q_STUCK",
        scenario=(
            "You've been stuck on a problem for 30 minutes. Nothing is clicking."
        ),
        options=[
            QuestionOption("A", "Open a blank doc and write out everything I know about it", {"clarity_strategy": "writing", "help_seeking_behavior": "independent"}),
            QuestionOption("B", "Ping a colleague or call someone who might know", {"clarity_strategy": "talking", "help_seeking_behavior": "proactive"}),
            QuestionOption("C", "Pick any solution and start building — action creates clarity", {"clarity_strategy": "acting", "help_seeking_behavior": "reactive"}),
            QuestionOption("D", "Close it, take a walk — answers come when I stop forcing", {"clarity_strategy": "waiting", "help_seeking_behavior": "independent"}),
        ],
        mode="quick",
    ),
    # ── Deep only (5 questions) ────────────────────────────────────────────────
    OnboardingQuestion(
        question_id="Q_FAILURE",
        scenario=(
            "You miss an important deadline for the first time in months."
        ),
        options=[
            QuestionOption("A", "Brief acknowledgment, reset, plan next steps — back to work same day", {"failure_response_pattern": "bounce_back"}),
            QuestionOption("B", "Spiral for 1–2 days, then gradually come back", {"failure_response_pattern": "freeze"}),
            QuestionOption("C", "Channel energy into another project, process in parallel", {"failure_response_pattern": "redirect"}),
        ],
        mode="deep",
    ),
    OnboardingQuestion(
        question_id="Q_HELP",
        scenario=(
            "You're 2 hours into a task and hit a wall a colleague could unblock in 5 minutes."
        ),
        options=[
            QuestionOption("A", "Ping them immediately — why suffer?", {"help_seeking_behavior": "proactive"}),
            QuestionOption("B", "Try for another 30 minutes first, then ask", {"help_seeking_behavior": "reactive"}),
            QuestionOption("C", "Keep grinding — asking feels like admitting defeat", {"help_seeking_behavior": "independent"}),
        ],
        mode="deep",
    ),
    OnboardingQuestion(
        question_id="Q_EXECUTION2",
        scenario=(
            "Thinking about your best-ever work outputs, they usually came from..."
        ),
        options=[
            QuestionOption("A", "Intense multi-day sprints where I blocked everything out", {"execution_pattern": "sprint"}),
            QuestionOption("B", "Consistent daily routines building steadily over weeks", {"execution_pattern": "marathon"}),
            QuestionOption("C", "Unpredictable bursts of inspiration where everything clicked", {"execution_pattern": "burst"}),
        ],
        mode="deep",
    ),
    OnboardingQuestion(
        question_id="Q_DECISION2",
        scenario=(
            "Your team is stuck and can't reach consensus. You..."
        ),
        options=[
            QuestionOption("A", "Propose a decision, own it, and invite pushback after", {"decision_style": "fast"}),
            QuestionOption("B", "Suggest one more round of input before deciding", {"decision_style": "deliberate"}),
            QuestionOption("C", "Stay quiet and hope someone else calls it", {"decision_style": "avoidant"}),
        ],
        mode="deep",
    ),
    OnboardingQuestion(
        question_id="Q_OVERLOAD2",
        scenario=(
            "When you're genuinely at your limit and overwhelmed, what actually helps?"
        ),
        options=[
            QuestionOption("A", "Cutting the list ruthlessly — only 2–3 items survive", {"overload_threshold": "low"}),
            QuestionOption("B", "A clear triage system and batching similar tasks", {"overload_threshold": "medium"}),
            QuestionOption("C", "More focus time and a clear execution sequence", {"overload_threshold": "high"}),
        ],
        mode="deep",
    ),
]

_Q_BY_ID: dict[str, OnboardingQuestion] = {q.question_id: q for q in _QUESTIONS}


# ── Service ────────────────────────────────────────────────────────────────────

class OnboardingService:
    @classmethod
    def get_questions(cls, mode: OnboardingMode) -> list[OnboardingQuestion]:
        if mode == OnboardingMode.QUICK:
            return [q for q in _QUESTIONS if q.mode == "quick"]
        return list(_QUESTIONS)  # deep = all questions

    @classmethod
    def score_answers(cls, answers: dict[str, str]) -> dict[str, str]:
        """
        Map {question_id: option_id} → {dimension: value}.

        Validates all IDs eagerly, then processes in canonical question order
        so that deep questions always overwrite quick ones for the same dimension.
        """
        for q_id, opt_id in answers.items():
            if q_id not in _Q_BY_ID:
                raise ValueError(f"Unknown question: {q_id!r}")
            question = _Q_BY_ID[q_id]
            if not any(o.option_id == opt_id for o in question.options):
                raise ValueError(f"Unknown option: {opt_id!r} for question {q_id!r}")

        result: dict[str, str] = {}
        for question in _QUESTIONS:  # canonical order
            if question.question_id not in answers:
                continue
            opt_id = answers[question.question_id]
            opt = next(o for o in question.options if o.option_id == opt_id)
            result.update(opt.scores)
        return result

    @classmethod
    def compute_profile(
        cls, dimension_scores: dict[str, str]
    ) -> tuple[dict[str, str], dict]:
        """
        Convert scored dimensions into (profile_data, computed_defaults).
        Missing dimensions get sensible defaults so the output always has all 9 keys.
        """
        profile_data: dict[str, str] = {
            "focus_stability":        dimension_scores.get("focus_stability", "medium"),
            "task_handling_style":    dimension_scores.get("task_handling_style", "sequential"),
            "decision_style":         dimension_scores.get("decision_style", "deliberate"),
            "overload_threshold":     dimension_scores.get("overload_threshold", "medium"),
            "interruption_behavior":  dimension_scores.get("interruption_behavior", "adaptive"),
            "clarity_strategy":       dimension_scores.get("clarity_strategy", "acting"),
            "execution_pattern":      dimension_scores.get("execution_pattern", "burst"),
            "help_seeking_behavior":  dimension_scores.get("help_seeking_behavior", "reactive"),
            "failure_response_pattern": dimension_scores.get("failure_response_pattern", "redirect"),
        }
        computed_defaults: dict = {
            "dominant_mode":            cls._derive_dominant_mode(profile_data),
            "energy_archetype":         "variable",  # updated from real check-in patterns
            "recommended_session_length": cls._derive_session_length(profile_data),
        }
        return profile_data, computed_defaults

    @classmethod
    def _derive_dominant_mode(cls, p: dict[str, str]) -> str:
        focus    = p["focus_stability"]
        overload = p["overload_threshold"]
        decision = p["decision_style"]
        execution = p["execution_pattern"]
        task     = p["task_handling_style"]
        clarity  = p["clarity_strategy"]
        failure  = p["failure_response_pattern"]
        help_s   = p["help_seeking_behavior"]

        # Recovery — checked first; signals of overload/avoidance override everything
        if focus == "low" and overload == "low":
            return "recovery"
        if decision == "avoidant" and failure == "freeze":
            return "recovery"

        # Achiever — high focus + fast decisions
        if focus == "high" and decision == "fast":
            return "achiever"

        # Creative — burst execution + parallel multitasking
        if execution == "burst" and task == "parallel":
            return "creative"

        # Clarity — writing-first + deliberate thinking
        if clarity == "writing" and decision == "deliberate":
            return "clarity"

        # Learning — actively seeks input + deliberate decisions
        if help_s == "proactive" and decision == "deliberate":
            return "learning"

        # Achiever (broader signal)
        if focus == "high" and execution == "sprint":
            return "achiever"

        return "harmony"

    @classmethod
    def _derive_session_length(cls, p: dict[str, str]) -> int:
        focus     = p["focus_stability"]
        execution = p["execution_pattern"]
        if focus == "high" and execution == "marathon":
            return 90
        if focus == "low":
            return 25
        return 45

    @classmethod
    def recalibrate_defaults(
        cls,
        base_defaults: dict,
        *,
        urge_events_last_30d: int,
        abandoned_sessions_last_30d: int,
        completed_sessions_last_30d: int,
    ) -> dict:
        """
        Update computed_defaults from recent behavioural signals.
        Returns a copy — never mutates the input.

        Thresholds:
          urge_events >= 10/30d  → recovery signals persistent struggle
          abandonment rate >= 50% → execution consistently breaks down
        """
        updated = dict(base_defaults)
        total = abandoned_sessions_last_30d + completed_sessions_last_30d
        abandonment_rate = abandoned_sessions_last_30d / total if total > 0 else 0.0

        if urge_events_last_30d >= 10 or abandonment_rate >= 0.5:
            updated["dominant_mode"] = "recovery"

        return updated
