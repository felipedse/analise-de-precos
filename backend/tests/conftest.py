"""Fixtures dos testes que precisam de PostgreSQL.

Usam o banco de `DATABASE_URL_TESTE` (padrão: `precos_teste` no PostgreSQL do docker-compose),
que é recriado e recebe a amostra de `backend/amostra/`. Sem PostgreSQL acessível, esses testes
são pulados; os testes dos coletores rodam sem banco.
"""

from __future__ import annotations

import asyncio
import os

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from precos import amostra

URL_TESTE = os.environ.get("DATABASE_URL_TESTE", "postgresql://precos:precos@localhost:5432/precos_teste")


def _recriar_banco(url: str) -> None:
    nome = conninfo_to_dict(url)["dbname"]
    manutencao = make_conninfo(url, dbname="postgres")
    with psycopg.connect(manutencao, autocommit=True, connect_timeout=3) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{nome}"')


async def _carregar(url: str) -> None:
    async with await psycopg.AsyncConnection.connect(url) as conn:
        await amostra.carregar(conn)


@pytest.fixture(scope="session")
def url_banco() -> str:
    try:
        _recriar_banco(URL_TESTE)
    except psycopg.OperationalError as e:
        pytest.skip(f"PostgreSQL de teste indisponível ({URL_TESTE}): {e}")
    asyncio.run(_carregar(URL_TESTE))
    return URL_TESTE


@pytest.fixture(scope="session")
def cliente(url_banco):
    from fastapi.testclient import TestClient

    from precos.api.app import criar_app

    with TestClient(criar_app(url_banco)) as c:
        yield c


@pytest.fixture
def banco(url_banco):
    with psycopg.connect(url_banco) as conn:
        yield conn
