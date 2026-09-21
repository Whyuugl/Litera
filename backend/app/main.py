import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.admin_catalog import router as admin_catalog_router
from app.api.routes.admin_memberships import router as admin_memberships_router
from app.api.routes.catalog import router as catalog_router
from app.api.routes.memberships import router as memberships_router
from app.api.routes.users import router as users_router
from app.core.security import auth_settings
from app.services.memberships import membership_duration_days


@asynccontextmanager
async def lifespan(_: FastAPI):
    auth_settings()
    membership_duration_days()
    yield


origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
if "*" in origins:
    raise RuntimeError("CORS_ORIGINS cannot contain '*' when credentials are enabled")

app = FastAPI(title="Litera API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(memberships_router, prefix="/api/v1")
app.include_router(admin_memberships_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(admin_catalog_router, prefix="/api/v1")


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "litera-api"}
