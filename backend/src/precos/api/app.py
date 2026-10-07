"""Aplicação FastAPI: `uv run precos api` ou `uvicorn precos.api.app:criar_app --factory`."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from precos import banco
from precos.api.rotas import rotas

# Build do front (`npm run build` em frontend/). Se existir, é servido junto com a API.
FRONT = Path(__file__).resolve().parents[4] / "frontend" / "dist"


def criar_app(url_banco: str | None = None) -> FastAPI:
    load_dotenv()

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        async with AsyncConnectionPool(
            url_banco or banco.url_banco(), min_size=1, max_size=8, kwargs={"row_factory": dict_row}, open=False
        ) as pool:
            app.state.pool = pool
            yield

    app = FastAPI(title="Preços SC", lifespan=ciclo_de_vida)
    app.include_router(rotas)

    if FRONT.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONT / "assets"), name="assets")

        @app.get("/{caminho:path}", include_in_schema=False)
        async def front(caminho: str) -> FileResponse:
            arquivo = FRONT / caminho
            if caminho and arquivo.is_file() and FRONT in arquivo.resolve().parents:
                return FileResponse(arquivo)
            return FileResponse(FRONT / "index.html")  # rotas do React Router

    return app
