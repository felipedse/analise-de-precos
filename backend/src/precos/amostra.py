"""Exporta e carrega a amostra de dados versionada em `backend/amostra/`.

A amostra é um CSV comprimido por tabela, com os ids originais, contendo a última
coleta bem-sucedida de cada rede escolhida.
"""

from __future__ import annotations

import gzip
import logging
from pathlib import Path

import psycopg
from psycopg import sql

from precos import banco

log = logging.getLogger(__name__)

PASTA_PADRAO = Path(__file__).resolve().parents[2] / "amostra"

# Ordem de carga respeita as chaves estrangeiras.
COLUNAS: dict[str, tuple[str, ...]] = {
    "rede": ("id", "slug", "nome", "plataforma", "site"),
    "loja": ("id", "rede_id", "codigo_externo", "nome", "cidade", "uf"),
    "produto": (
        "id", "rede_id", "sku", "nome", "marca", "ean", "categoria", "unidade", "fator_unidade", "url",
        "imagem_url", "criado_em", "atualizado_em",
    ),
    "coleta": ("id", "rede_id", "iniciada_em", "finalizada_em", "status", "total_precos", "erros", "mensagem"),
    "preco": (
        "id", "produto_id", "loja_id", "coleta_id", "coletado_em", "preco", "preco_regular", "em_promocao",
        "disponivel", "estoque",
    ),
}

# Linhas de cada tabela que entram na amostra; %(coletas)s são os ids das coletas exportadas.
FILTROS = {
    "rede": "id IN (SELECT rede_id FROM coleta WHERE id = ANY(%(coletas)s))",
    "loja": "id IN (SELECT DISTINCT loja_id FROM preco WHERE coleta_id = ANY(%(coletas)s))",
    "produto": "id IN (SELECT DISTINCT produto_id FROM preco WHERE coleta_id = ANY(%(coletas)s))",
    "coleta": "id = ANY(%(coletas)s)",
    "preco": "coleta_id = ANY(%(coletas)s)",
}


def _arquivo(pasta: Path, tabela: str) -> Path:
    return pasta / f"{tabela}.csv.gz"


async def exportar(conn: psycopg.AsyncConnection, redes: list[str], pasta: Path = PASTA_PADRAO) -> dict[str, int]:
    """Grava a última coleta `ok` de cada rede em `pasta`. Devolve o número de linhas por tabela."""
    cur = await conn.execute(
        """
        SELECT DISTINCT ON (r.slug) r.slug, c.id
        FROM coleta c JOIN rede r ON r.id = c.rede_id
        WHERE r.slug = ANY(%s) AND c.status = 'ok' AND c.total_precos > 0
        ORDER BY r.slug, c.id DESC
        """,
        (redes,),
    )
    coletas = dict(await cur.fetchall())
    faltando = set(redes) - set(coletas)
    if faltando:
        raise ValueError(f"sem coleta bem-sucedida para: {', '.join(sorted(faltando))}")

    pasta.mkdir(parents=True, exist_ok=True)
    contagens = {}
    for tabela, colunas in COLUNAS.items():
        consulta = sql.SQL("COPY (SELECT {} FROM {} WHERE {} ORDER BY id) TO STDOUT WITH (FORMAT csv, HEADER)").format(
            sql.SQL(", ").join(map(sql.Identifier, colunas)),
            sql.Identifier(tabela),
            sql.SQL(FILTROS[tabela]),
        )
        # mtime=0 deixa o .gz idêntico quando o conteúdo não muda (diffs limpos no Git).
        with open(_arquivo(pasta, tabela), "wb") as bruto, gzip.GzipFile(
            filename="", mode="wb", fileobj=bruto, mtime=0
        ) as saida:
            async with conn.cursor() as c:
                async with c.copy(consulta, {"coletas": list(coletas.values())}) as copy:
                    async for bloco in copy:
                        saida.write(bloco)
                contagens[tabela] = c.rowcount
        log.info("amostra: %s com %d linhas", tabela, contagens[tabela])
    return contagens


async def carregar(conn: psycopg.AsyncConnection, pasta: Path = PASTA_PADRAO, substituir: bool = False) -> dict[str, int]:
    """Carrega a amostra num banco vazio (ou apaga tudo antes, com `substituir`)."""
    await banco.criar_schema(conn)
    cur = await conn.execute("SELECT EXISTS (SELECT 1 FROM rede)")
    if (await cur.fetchone())[0]:
        if not substituir:
            raise ValueError("o banco já tem dados; use --substituir para apagá-los e carregar a amostra")
        await conn.execute("TRUNCATE preco, coleta, produto, loja, rede RESTART IDENTITY CASCADE")

    contagens = {}
    for tabela, colunas in COLUNAS.items():
        consulta = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER)").format(
            sql.Identifier(tabela), sql.SQL(", ").join(map(sql.Identifier, colunas))
        )
        async with conn.cursor() as c:
            async with c.copy(consulta) as copy:
                with gzip.open(_arquivo(pasta, tabela), "rb") as entrada:
                    while bloco := entrada.read(1 << 20):
                        await copy.write(bloco)
            contagens[tabela] = c.rowcount
        # Os ids vieram do arquivo: a sequence precisa continuar depois do maior deles.
        await conn.execute(
            sql.SQL("SELECT setval(pg_get_serial_sequence({t}, 'id'), coalesce(max(id), 1), max(id) IS NOT NULL) FROM {i}").format(
                t=sql.Literal(tabela), i=sql.Identifier(tabela)
            )
        )
        log.info("amostra: %s com %d linhas carregadas", tabela, contagens[tabela])
    await conn.commit()
    await banco.atualizar_analise(conn)
    return contagens
