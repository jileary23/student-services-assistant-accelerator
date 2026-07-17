import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from azure.identity.aio import DefaultAzureCredential
from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agent import create_answer_generator
from app.config import get_settings
from app.retrieval import create_retriever
from app.schemas import ChatRequest, ChatResponse
from app.service import StudentServicesService

settings = get_settings()
static_path = Path(__file__).parent / "static"

if settings.applicationinsights_connection_string:
    configure_azure_monitor(logger_name="student_services")

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    credential = DefaultAzureCredential() if settings.app_mode == "azure" else None
    app.state.credential = credential
    app.state.service = StudentServicesService(
        settings,
        create_retriever(settings, credential),
        create_answer_generator(settings, credential),
    )
    yield
    await app.state.service.close()
    if credential:
        await credential.close()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=static_path), name="static")
app.mount(
    "/knowledge",
    StaticFiles(directory=settings.knowledge_path, html=False),
    name="knowledge",
)


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(static_path / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": settings.app_mode}


@app.get("/api/config")
async def public_config() -> dict[str, str | None]:
    return {
        "institution_name": settings.institution_name,
        "university_website": settings.university_website,
        "support_destination": settings.support_destination,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    service: StudentServicesService = request.app.state.service
    return await service.chat(payload)
