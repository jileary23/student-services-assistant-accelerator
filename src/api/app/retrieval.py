import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from azure.core.credentials_async import AsyncTokenCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import QueryType, VectorizableTextQuery, VectorQuery

from app.config import Settings
from app.schemas import Citation


@dataclass(frozen=True)
class SearchResult:
    citations: list[Citation]
    has_evidence: bool


class Retriever(Protocol):
    async def search(self, query: str, *, top: int = 5) -> SearchResult: ...

    async def close(self) -> None: ...


class LocalKnowledgeRetriever:
    def __init__(self, knowledge_path: Path) -> None:
        self._documents = _load_markdown_documents(knowledge_path)

    async def search(self, query: str, *, top: int = 5) -> SearchResult:
        terms = _terms(query)
        ranked = sorted(
            self._documents,
            key=lambda document: _term_score(terms, document.excerpt),
            reverse=True,
        )
        citations = [
            document for document in ranked[:top] if _term_score(terms, document.excerpt) > 0
        ]
        return SearchResult(citations=citations, has_evidence=bool(citations))

    async def close(self) -> None:
        return None


class AzureSearchRetriever:
    def __init__(self, settings: Settings, credential: AsyncTokenCredential) -> None:
        if not settings.azure_search_endpoint:
            raise ValueError("AZURE_SEARCH_ENDPOINT is required in azure mode.")
        self._settings = settings
        self._client = SearchClient(
            endpoint=settings.azure_search_endpoint,
            index_name=settings.azure_search_index_name,
            credential=credential,
        )

    async def search(self, query: str, *, top: int = 5) -> SearchResult:
        vector_queries: list[VectorQuery] | None = None
        if self._settings.azure_search_vector_enabled:
            vector_queries = [
                VectorizableTextQuery(
                    text=query,
                    fields="content_vector",
                    k_nearest_neighbors=50,
                )
            ]

        results = await self._client.search(
            search_text=query,
            vector_queries=vector_queries,
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name=self._settings.azure_search_semantic_configuration,
            query_caption="extractive",
            select=["id", "title", "content", "source_url"],
            top=top,
        )
        citations = [
            Citation(
                id=str(result["id"]),
                title=str(result["title"]),
                source_url=result.get("source_url"),
                excerpt=_caption_or_content(result),
            )
            async for result in results
        ]
        return SearchResult(citations=citations, has_evidence=bool(citations))

    async def close(self) -> None:
        await self._client.close()


def create_retriever(
    settings: Settings, credential: AsyncTokenCredential | None = None
) -> Retriever:
    if settings.app_mode == "azure":
        if credential is None:
            raise ValueError("An Azure credential is required in azure mode.")
        return AzureSearchRetriever(settings, credential)
    return LocalKnowledgeRetriever(settings.knowledge_path)


def _load_markdown_documents(path: Path) -> list[Citation]:
    documents: list[Citation] = []
    for file_path in sorted(path.glob("*.md")):
        content = file_path.read_text(encoding="utf-8")
        title = _extract_title(content, file_path.stem.replace("-", " ").title())
        documents.append(
            Citation(
                id=file_path.stem,
                title=title,
                source_url=_source_url(content, f"/knowledge/{file_path.name}"),
                excerpt=_normalize_markdown(content),
            )
        )
    return documents


def _extract_title(content: str, fallback: str) -> str:
    first_line = content.splitlines()[0] if content else ""
    return first_line.removeprefix("# ").strip() or fallback


def _normalize_markdown(content: str) -> str:
    without_headings = re.sub(r"^#+\s+", "", content, flags=re.MULTILINE)
    return " ".join(without_headings.split())[:1_200]


def _source_url(content: str, fallback: str) -> str:
    match = re.search(r"^Source:\s*(https://\S+)\s*$", content, flags=re.MULTILINE)
    return match.group(1) if match else fallback


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", value.lower()) if len(term) > 2}


def _term_score(query_terms: set[str], content: str) -> int:
    content_terms = _terms(content)
    return len(query_terms & content_terms)


def _caption_or_content(result: dict[str, object]) -> str:
    captions = result.get("@search.captions")
    if isinstance(captions, list) and captions:
        caption = captions[0]
        text = getattr(caption, "text", None)
        if text:
            return str(text)
    return str(result.get("content", ""))[:800]
