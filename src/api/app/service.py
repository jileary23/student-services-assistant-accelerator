import logging
from uuid import uuid4

from app.agent import AnswerGenerator
from app.config import Settings
from app.retrieval import Retriever
from app.safety import assess_request
from app.schemas import ChatRequest, ChatResponse, Escalation

logger = logging.getLogger("student_services")


class StudentServicesService:
    def __init__(
        self,
        settings: Settings,
        retriever: Retriever,
        generator: AnswerGenerator,
    ) -> None:
        self._settings = settings
        self._retriever = retriever
        self._generator = generator

    async def chat(self, request: ChatRequest) -> ChatResponse:
        conversation_id = request.conversation_id or str(uuid4())
        decision = assess_request(request.message)

        if decision.action == "clarify":
            return ChatResponse(
                answer="Could you share a little more detail about what you need?",
                confidence="low",
                escalation=Escalation(required=False),
                conversation_id=conversation_id,
            )

        if decision.action == "escalate":
            logger.info("student_services_escalation", extra={"reason": decision.reason})
            return ChatResponse(
                answer=(
                    f"I cannot complete that request here. {decision.reason} "
                    f"I can connect you with the {self._settings.support_destination}."
                ),
                confidence="low",
                escalation=Escalation(
                    required=True,
                    reason=decision.reason,
                    destination=self._settings.support_destination,
                ),
                conversation_id=conversation_id,
            )

        evidence = await self._retriever.search(request.message)
        if not evidence.has_evidence:
            logger.info("student_services_no_evidence")
            return ChatResponse(
                answer=(
                    "I could not find that in the approved information. "
                    f"Please contact the {self._settings.support_destination}."
                ),
                confidence="low",
                escalation=Escalation(
                    required=True,
                    reason="No approved source matched the question.",
                    destination=self._settings.support_destination,
                ),
                conversation_id=conversation_id,
            )

        answer = await self._generator.generate(request.message, evidence.citations)
        logger.info(
            "student_services_answer",
            extra={"citation_count": len(evidence.citations)},
        )
        return ChatResponse(
            answer=answer,
            citations=evidence.citations,
            confidence="high" if len(evidence.citations) > 1 else "medium",
            escalation=Escalation(required=False),
            conversation_id=conversation_id,
        )

    async def close(self) -> None:
        await self._retriever.close()
        await self._generator.close()
