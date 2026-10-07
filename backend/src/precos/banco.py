from __future__ import annotations

import os
from datetime import datetime, timezone
from importlib import resources

import psycopg

from precos.modelos import Loja, Oferta, Rede

URL_PADRAO = "postgresql://precos:precos@localhost:5432/precos"

UPSERT_PRODUTOS = """
INSERT INTO produto (rede_id, sku, nome, marca, ean, categoria, unidade, fator_unidade, url, imagem_url)
SELECT %(rede_id)s, *
FROM unnest(
    %(sku)s::text[], %(nome)s::text[], %(marca)s::text[], %(ean)s::text[], %(categoria)s::text[],
    %(unidade)s::text[], %(fator_unidade)s::numeric[], %(url)s::text[], %(imagem_url)s::text[]
)
ON CONFLICT (rede_id, sku) DO UPDATE SET
    nome          = EXCLUDED.nome,
    marca         = COALESCE(EXCLUDED.marca, produto.marca),
    ean           = COALESCE(EXCLUDED.ean, produto.ean),
    categoria     = COALESCE(EXCLUDED.categoria, produto.categoria),
    unidade       = COALESCE(EXCLUDED.unidade, produto.unidade),
    fator_unidade = COALESCE(EXCLUDED.fator_unidade, produto.fator_unidade),
    url           = COALESCE(EXCLUDED.url, produto.url),
    imagem_url    = COALESCE(EXCLUDED.imagem_url, produto.imagem_url),
    atualizado_em = now()
RETURNING id, sku
"""

CAMPOS_PRODUTO = ("sku", "nome", "marca", "ean", "categoria", "unidade", "fator_unidade", "url", "imagem_url")


def url_banco() -> str:
    return os.environ.get("DATABASE_URL", URL_PADRAO)


async def conectar() -> psycopg.AsyncConnection:
    return await psycopg.AsyncConnection.connect(url_banco())


async def criar_schema(conn: psycopg.AsyncConnection) -> None:
    sql = resources.files("precos").joinpath("schema.sql").read_text(encoding="utf-8")
    await conn.execute(sql)
    await conn.commit()


class Gravador:
    """Grava uma coleta de uma rede no banco."""

    def __init__(self, conn: psycopg.AsyncConnection, rede: Rede) -> None:
        self.conn = conn
        self.rede = rede
        self.rede_id: int | None = None
        self.coleta_id: int | None = None
        self.lojas: dict[str, int] = {}
        self.produtos: dict[str, int] = {}  # sku -> id, já gravados nesta coleta
        self.total_precos = 0

    async def iniciar(self, lojas: list[Loja]) -> None:
        r = self.rede
        cur = await self.conn.execute(
            """
            INSERT INTO rede (slug, nome, plataforma, site) VALUES (%s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET nome = EXCLUDED.nome, plataforma = EXCLUDED.plataforma,
                site = EXCLUDED.site
            RETURNING id
            """,
            (r.slug, r.nome, r.plataforma, r.site),
        )
        self.rede_id = (await cur.fetchone())[0]

        for loja in lojas:
            cur = await self.conn.execute(
                """
                INSERT INTO loja (rede_id, codigo_externo, nome, cidade, uf) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (rede_id, codigo_externo) DO UPDATE SET nome = EXCLUDED.nome,
                    cidade = EXCLUDED.cidade, uf = EXCLUDED.uf
                RETURNING id
                """,
                (self.rede_id, loja.codigo, loja.nome, loja.cidade, loja.uf),
            )
            self.lojas[loja.codigo] = (await cur.fetchone())[0]

        cur = await self.conn.execute("INSERT INTO coleta (rede_id) VALUES (%s) RETURNING id", (self.rede_id,))
        self.coleta_id = (await cur.fetchone())[0]
        await self.conn.commit()

    async def gravar(self, ofertas: list[Oferta]) -> None:
        if not ofertas:
            return
        await self._gravar_produtos(ofertas)

        agora = datetime.now(timezone.utc)
        async with self.conn.cursor() as cur:
            async with cur.copy(
                "COPY preco (produto_id, loja_id, coleta_id, coletado_em, preco, preco_regular,"
                " em_promocao, disponivel, estoque) FROM STDIN"
            ) as copy:
                for o in ofertas:
                    await copy.write_row((
                        self.produtos[o.sku], self.lojas[o.loja_codigo], self.coleta_id, agora,
                        o.preco, o.preco_regular, o.em_promocao, o.disponivel, o.estoque,
                    ))
        await self.conn.commit()
        self.total_precos += len(ofertas)

    async def _gravar_produtos(self, ofertas: list[Oferta]) -> None:
        # Cada produto é atualizado uma vez por coleta (o Osuper repete o produto em cada loja).
        novos = {o.sku: o for o in ofertas if o.sku not in self.produtos}
        if not novos:
            return
        params = {campo: [getattr(o, campo) for o in novos.values()] for campo in CAMPOS_PRODUTO}
        params["rede_id"] = self.rede_id
        cur = await self.conn.execute(UPSERT_PRODUTOS, params)
        for produto_id, sku in await cur.fetchall():
            self.produtos[sku] = produto_id

    async def finalizar(self, status: str, erros: int, mensagem: str | None = None) -> None:
        await self.conn.rollback()  # descarta um lote pela metade, se houver
        await self.conn.execute(
            """
            UPDATE coleta SET finalizada_em = now(), status = %s, total_precos = %s, erros = %s, mensagem = %s
            WHERE id = %s
            """,
            (status, self.total_precos, erros, mensagem, self.coleta_id),
        )
        await self.conn.commit()


async def atualizar_analise(conn: psycopg.AsyncConnection) -> None:
    """Recalcula a view materializada `preco_analise` (último preço por produto e loja)."""
    await conn.commit()  # REFRESH ... CONCURRENTLY não roda dentro de transação aberta
    await conn.set_autocommit(True)
    try:
        await conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY preco_analise")
    finally:
        await conn.set_autocommit(False)
