import argparse
import os
import re
from pathlib import Path

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from openai import AzureOpenAI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index approved student-services content.")
    parser.add_argument("--source", type=Path, default=Path("data/knowledge"))
    parser.add_argument("--index", default=os.getenv("AZURE_SEARCH_INDEX_NAME", "student-services"))
    parser.add_argument("--with-vectors", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    endpoint = required_env("AZURE_SEARCH_ENDPOINT")
    credential = DefaultAzureCredential()
    documents = load_documents(args.source)

    if args.with_vectors:
        add_embeddings(documents, credential)

    index = build_index(args.index, with_vectors=args.with_vectors)
    index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
    index_client.create_or_update_index(index)

    search_client = SearchClient(endpoint=endpoint, index_name=args.index, credential=credential)
    result = search_client.upload_documents(documents)
    failed = [item.key for item in result if not item.succeeded]
    if failed:
        raise RuntimeError(f"Failed to index documents: {', '.join(failed)}")
    print(f"Indexed {len(documents)} approved documents into '{args.index}'.")


def build_index(name: str, *, with_vectors: bool) -> SearchIndex:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="source_url", type=SearchFieldDataType.String),
    ]
    vector_search = None
    if with_vectors:
        dimensions = int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "1536"))
        fields.append(
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=dimensions,
                vector_search_profile_name="student-services-vector-profile",
            )
        )
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="student-services-hnsw")],
            profiles=[
                VectorSearchProfile(
                    name="student-services-vector-profile",
                    algorithm_configuration_name="student-services-hnsw",
                    vectorizer_name="student-services-vectorizer",
                )
            ],
            vectorizers=[
                AzureOpenAIVectorizer(
                    vectorizer_name="student-services-vectorizer",
                    parameters=AzureOpenAIVectorizerParameters(
                        resource_url=required_env("AZURE_OPENAI_ENDPOINT"),
                        deployment_name=os.getenv(
                            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
                        ),
                        model_name="text-embedding-3-small",
                    ),
                )
            ],
        )

    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="student-services-semantic",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[SemanticField(field_name="content")],
                ),
            )
        ]
    )
    return SearchIndex(
        name=name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )


def load_documents(source: Path) -> list[dict[str, object]]:
    documents: list[dict[str, object]] = []
    for path in sorted(source.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        title = content.splitlines()[0].removeprefix("# ").strip()
        documents.append(
            {
                "id": path.stem,
                "title": title,
                "content": normalize_markdown(content),
                "source_url": source_url(content, f"/knowledge/{path.name}"),
            }
        )
    if not documents:
        raise ValueError(f"No Markdown documents found in {source}.")
    return documents


def add_embeddings(
    documents: list[dict[str, object]], credential: DefaultAzureCredential
) -> None:
    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )
    client = AzureOpenAI(
        azure_endpoint=required_env("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        azure_ad_token_provider=token_provider,
    )
    deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
    response = client.embeddings.create(
        model=deployment,
        input=[str(document["content"]) for document in documents],
    )
    for document, embedding in zip(documents, response.data, strict=True):
        document["content_vector"] = embedding.embedding


def normalize_markdown(content: str) -> str:
    return " ".join(re.sub(r"^#+\s+", "", content, flags=re.MULTILINE).split())


def source_url(content: str, fallback: str) -> str:
    match = re.search(r"^Source:\s*(https://\S+)\s*$", content, flags=re.MULTILINE)
    return match.group(1) if match else fallback


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} is required.")
    return value


if __name__ == "__main__":
    main()
