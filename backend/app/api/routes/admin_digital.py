import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile, status
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.api.dependencies import AdminUser, DatabaseSession
from app.models import AccessLevel
from app.schemas.digital import ChapterCreate, ChapterResponse, ChapterUpdate, DigitalUploadResponse
from app.schemas.rag import RAGIndexResponse, RetrievalResult, RetrievalSearch
from app.schemas.catalog import DigitalFileCreate
from app.services import digital
from app.services import catalog
from app.services.storage import StorageError
from app.services import rag


router = APIRouter(prefix="/admin", tags=["admin digital"])


def _raise(exc: Exception) -> HTTPException:
    if isinstance(exc, digital.DigitalNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Digital resource not found")
    if isinstance(exc, (ValueError, digital.InvalidPdf, StorageError)):
        return HTTPException(status.HTTP_400_BAD_REQUEST, str(exc) or "Invalid PDF")
    return HTTPException(status.HTTP_409_CONFLICT, str(exc) or "Digital resource conflict")


def _raise_rag(exc: Exception) -> HTTPException:
    if isinstance(exc, rag.RAGNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Digital resource not found")
    if isinstance(exc, rag.RAGConflict):
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc) or "RAG service unavailable")


@router.post("/editions/{edition_id}/digital-files", response_model=DigitalUploadResponse, status_code=201)
async def upload(
    edition_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
):
    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            return catalog.create_digital_file(
                session, edition_id, DigitalFileCreate.model_validate(await request.json()), admin
            )
        form = await request.form()
        file = form.get("file")
        if not isinstance(file, StarletteUploadFile):
            raise digital.InvalidPdf("Choose a PDF file")
        access_level = AccessLevel(str(form.get("access_level", AccessLevel.REGISTERED.value)))
        allow_download = str(form.get("allow_download", "false")).lower() == "true"
        try:
            return digital.upload_pdf(session, edition_id, file, access_level, allow_download, admin)
        finally:
            await file.close()
    except catalog.InvalidCatalogReference as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid catalog reference") from exc
    except (ValueError, digital.DigitalNotFound, digital.DigitalConflict, digital.InvalidPdf, StorageError) as exc:
        raise _raise(exc) from exc


@router.post("/digital-files/{file_id}/replace", response_model=DigitalUploadResponse)
def replace(file_id: uuid.UUID, session: DatabaseSession, admin: AdminUser, file: Annotated[UploadFile, File()]):
    try:
        return digital.replace_pdf(session, file_id, file, admin)
    except (digital.DigitalNotFound, digital.DigitalConflict, digital.InvalidPdf, StorageError) as exc:
        raise _raise(exc) from exc


@router.post("/digital-files/{file_id}/process", response_model=DigitalUploadResponse)
def process(file_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return digital.retry_processing(session, file_id)
    except (digital.DigitalNotFound, digital.DigitalConflict, StorageError) as exc:
        raise _raise(exc) from exc


@router.get("/editions/{edition_id}/chapters", response_model=list[ChapterResponse])
def chapters(edition_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return digital.list_chapters(session, edition_id)
    except digital.DigitalNotFound as exc:
        raise _raise(exc) from exc


@router.post("/editions/{edition_id}/chapters", response_model=ChapterResponse, status_code=201)
def create_chapter(edition_id: uuid.UUID, data: ChapterCreate, session: DatabaseSession, _: AdminUser):
    try:
        return digital.create_chapter(session, edition_id, data)
    except (digital.DigitalNotFound, digital.DigitalConflict) as exc:
        raise _raise(exc) from exc


@router.patch("/chapters/{chapter_id}", response_model=ChapterResponse)
def update_chapter(chapter_id: uuid.UUID, data: ChapterUpdate, session: DatabaseSession, _: AdminUser):
    try:
        return digital.update_chapter(session, chapter_id, data)
    except (digital.DigitalNotFound, digital.DigitalConflict) as exc:
        raise _raise(exc) from exc


@router.delete("/chapters/{chapter_id}", status_code=204)
def delete_chapter(chapter_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        digital.delete_chapter(session, chapter_id)
    except (digital.DigitalNotFound, digital.DigitalConflict) as exc:
        raise _raise(exc) from exc
    return Response(status_code=204)


@router.get("/digital-files/{file_id}/rag", response_model=RAGIndexResponse)
def rag_status(file_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return rag.get_status(session, file_id)
    except rag.RAGNotFound as exc:
        raise _raise_rag(exc) from exc


@router.post("/digital-files/{file_id}/rag/index", response_model=RAGIndexResponse)
async def index_rag(file_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return await rag.ingest(session, file_id)
    except (rag.RAGNotFound, rag.RAGConflict, rag.RAGUnavailable) as exc:
        raise _raise_rag(exc) from exc


@router.post("/digital-files/{file_id}/rag/reindex", response_model=RAGIndexResponse)
async def reindex_rag(file_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return await rag.ingest(session, file_id, force=True)
    except (rag.RAGNotFound, rag.RAGConflict, rag.RAGUnavailable) as exc:
        raise _raise_rag(exc) from exc


@router.post("/editions/{edition_id}/rag/search", response_model=list[RetrievalResult])
async def search_rag(
    edition_id: uuid.UUID,
    data: RetrievalSearch,
    session: DatabaseSession,
    _: AdminUser,
):
    try:
        return await rag.search(session, edition_id, data.query, top_k=data.top_k)
    except (rag.RAGNotFound, rag.RAGConflict, rag.RAGUnavailable) as exc:
        raise _raise_rag(exc) from exc
