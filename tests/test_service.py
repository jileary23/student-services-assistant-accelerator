from app.config import Settings
from app.retrieval import SearchResult
from app.schemas import ChatRequest, Citation
from app.service import StudentServicesService


class StubRetriever:
    def __init__(self, citations: list[Citation]) -> None:
        self.citations = citations

    async def search(self, query: str, *, top: int = 5) -> SearchResult:
        return SearchResult(citations=self.citations, has_evidence=bool(self.citations))

    async def close(self) -> None:
        return None


class StubGenerator:
    async def generate(self, question: str, citations: list[Citation]) -> str:
        return f"Registration opens April 15. [{citations[0].id}]"

    async def close(self) -> None:
        return None


async def test_grounded_answer_includes_citations() -> None:
    citation = Citation(
        id="registration",
        title="Registration",
        excerpt="Fall registration opens April 15.",
    )
    service = StudentServicesService(
        Settings(),
        StubRetriever([citation]),
        StubGenerator(),
    )

    response = await service.chat(ChatRequest(message="When does fall registration open?"))

    assert response.confidence == "medium"
    assert response.citations == [citation]
    assert response.escalation.required is False


async def test_missing_evidence_routes_to_staff() -> None:
    service = StudentServicesService(Settings(), StubRetriever([]), StubGenerator())

    response = await service.chat(ChatRequest(message="What is the aviation lab fee?"))

    assert response.confidence == "low"
    assert response.escalation.required is True
    assert response.citations == []


async def test_account_request_skips_retrieval_and_routes_to_staff() -> None:
    service = StudentServicesService(Settings(), StubRetriever([]), StubGenerator())

    response = await service.chat(ChatRequest(message="Check my application status"))

    assert response.escalation.required is True
    assert "authentication" in response.escalation.reason.lower()
