"""Точка входа серверного приложения AuditXP (FastAPI + Uvicorn)."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routers import auth, etl, heatmap, misc, reports, risks, users
from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.session import dispose_engine, get_sessionmaker, init_models

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")

DESCRIPTION = (
    "REST API модуля корпоративного риск-менеджмента на основе данных "
    "внутреннего аудита. Разработчик ООО «Голдберг-Софт».")
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
}
CSP = ("default-src 'self'; img-src 'self' data:; "
       "style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.auto_create_schema:
        await init_models()
    if settings.seed_demo:
        from app.seed import seed_demo

        async with get_sessionmaker()() as session:
            await seed_demo(session)
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AuditXP: Риск-менеджмент API", version=__version__,
                  description=DESCRIPTION, lifespan=lifespan,
                  docs_url="/api/docs", redoc_url=None,
                  openapi_url="/api/openapi.json")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list,
                       allow_methods=["*"], allow_headers=["*"],
                       allow_credentials=True)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        if not request.url.path.startswith("/api/docs"):
            response.headers["Content-Security-Policy"] = CSP
        return response

    @app.exception_handler(DomainError)
    async def domain_error(_request: Request, exc: DomainError):
        return JSONResponse({"detail": exc.message},
                            status_code=exc.status_code)

    for module in (auth, etl, risks, heatmap, reports, users, misc):
        app.include_router(module.router, prefix="/api/v1")
    _mount_frontend(app, Path(settings.frontend_dist))
    return app


def _mount_frontend(app: FastAPI, dist: Path) -> None:
    """Раздача собранного React-клиента, если он есть (режим демо)."""
    index = dist / "index.html"
    if not index.exists():
        return
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"),
                  name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        target = dist / path
        if path and target.is_file() and dist in target.resolve().parents:
            return FileResponse(target)
        return FileResponse(index)


app = create_app()
