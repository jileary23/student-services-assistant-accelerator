import re

from app.schemas import RouteDecision

_DECISION_PATTERNS = (
    r"\b(approve|deny|decide)\b.*\b(admission|application|aid|appeal)\b",
    r"\b(am i|was i|will i be)\b.*\b(admitted|accepted|eligible|awarded)\b",
    r"\b(change|override|waive)\b.*\b(grade|decision|requirement|policy)\b",
)

_ACCOUNT_PATTERNS = (
    r"\b(my|mine)\b.*\b(application|balance|financial aid|grade|record|status)\b",
    r"\b(reset|unlock)\b.*\b(password|account)\b",
    r"\b(book|cancel|reschedule)\b.*\b(appointment|advising)\b",
)

_URGENT_PATTERNS = (
    r"\b(immediate danger|unsafe|suicid|self-harm)\b",
    r"\b(harassment|assault|threat)\b",
)


def assess_request(message: str) -> RouteDecision:
    normalized = " ".join(message.lower().split())

    if _matches_any(normalized, _URGENT_PATTERNS):
        return RouteDecision(
            action="escalate",
            reason="This request may require immediate support from a trained staff member.",
        )

    if _matches_any(normalized, _DECISION_PATTERNS):
        return RouteDecision(
            action="escalate",
            reason="The assistant cannot make or predict institutional decisions.",
        )

    if _matches_any(normalized, _ACCOUNT_PATTERNS):
        return RouteDecision(
            action="escalate",
            reason="Account-specific requests require authentication and an approved workflow.",
        )

    if len(normalized.split()) < 3:
        return RouteDecision(
            action="clarify",
            reason="The request needs a little more detail before searching approved content.",
        )

    return RouteDecision(
        action="answer",
        reason="The request can be answered from institution-approved information.",
    )


def _matches_any(message: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, message) for pattern in patterns)
