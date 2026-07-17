import pytest
from app.safety import assess_request


@pytest.mark.parametrize(
    "message",
    [
        "Was I accepted to the nursing program?",
        "Can you approve my financial aid appeal?",
        "Please waive the residency policy for me.",
    ],
)
def test_institutional_decisions_are_escalated(message: str) -> None:
    decision = assess_request(message)

    assert decision.action == "escalate"
    assert "decision" in decision.reason.lower()


@pytest.mark.parametrize(
    "message",
    [
        "Check my application status",
        "Reset my account password",
        "Book an advising appointment for me",
    ],
)
def test_account_specific_requests_require_an_approved_workflow(message: str) -> None:
    decision = assess_request(message)

    assert decision.action == "escalate"
    assert "authentication" in decision.reason.lower()


def test_general_policy_question_can_use_approved_content() -> None:
    decision = assess_request("When is the fall registration deadline?")

    assert decision.action == "answer"


def test_underspecified_question_requests_clarification() -> None:
    decision = assess_request("Financial aid")

    assert decision.action == "clarify"
