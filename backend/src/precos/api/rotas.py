"""Endpoints da API. Tudo é lido de `preco_analise` (último preço por produto e loja)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any, Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from psycopg import sql

from precos.api.estatisticas import AGREGADOS, estatisticas, sem_estatisticas
from precos.api.filtros import Filtros, filtros

rotas = APIRouter(prefix="/api")


async def conexao(request: Request) -> AsyncIterator[psycopg.AsyncConnection]:
    async with request.app.state.pool.connection() as conn:
        yield conn


async def _todas(conn: psycopg.AsyncConnection, consulta: sql.Composable, params: dict[str, Any]) -> list[dict]:
    cur = await conn.execute(consulta, params)
    return await cur.fetchall()


def _sem_decimal(linha: dict[str, Any]) -> dict[str, Any]:
    """Valores numeric viram número no JSON (o FastAPI serializaria Decimal como texto)."""
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in linha.items()}


def _com_estatisticas(linha: dict[str, Any]) -> dict[str, Any]:
    campos = {k: v for k, v in sem_estatisticas(linha).items() if k != "total"}
    return {**campos, "estatisticas": estatisticas(linha)}


@rotas.get("/meta")
async def meta(conn: psycopg.AsyncConnection = Depends(conexao)) -> dict[str, Any]:
    """Redes, lojas e marcas disponíveis para os filtros, e a data da última coleta de cada rede."""
    redes = await _todas(conn, sql.SQL("""
        SELECT r.slug, r.nome, u.finalizada_em AS ultima_coleta
        FROM rede r
        LEFT JOIN LATERAL (
            SELECT finalizada_em FROM coleta c WHERE c.rede_id = r.id AND c.status = 'ok' ORDER BY c.id DESC LIMIT 1
        ) u ON true
        WHERE EXISTS (SELECT 1 FROM preco_analise a WHERE a.rede_id = r.id)
        ORDER BY r.nome
    """), {})
    lojas = await _todas(conn, sql.SQL("""
        SELECT loja_id AS id, loja AS nome, rede, rede_nome, count(*) AS n
        FROM preco_analise GROUP BY 1, 2, 3, 4 ORDER BY rede_nome, nome
    """), {})
    marcas = await _todas(conn, sql.SQL("""
        SELECT marca, count(*) AS n FROM preco_analise WHERE marca IS NOT NULL
        GROUP BY marca ORDER BY n DESC, marca
    """), {})
    return {"redes": redes, "lojas": lojas, "marcas": marcas}


@rotas.get("/lojas")
async def lojas(f: Filtros = Depends(filtros), conn: psycopg.AsyncConnection = Depends(conexao)) -> dict[str, Any]:
    """Uma linha por loja e o total do conjunto filtrado (não é a soma das linhas)."""
    where, params = f.where()
    linhas = await _todas(conn, sql.SQL("""
        SELECT loja_id, loja, rede, rede_nome, GROUPING(loja_id) = 1 AS total, {agregados}
        FROM preco_analise {where}
        GROUP BY GROUPING SETS ((loja_id, loja, rede, rede_nome), ())
        ORDER BY total, rede_nome, loja
    """).format(agregados=AGREGADOS, where=where), params)
    total = next((linha for linha in linhas if linha["total"]), None)
    return {
        "linhas": [_com_estatisticas(linha) for linha in linhas if not linha["total"]],
        "total": estatisticas(total or {}),
    }


def _filhos(where: sql.Composable, agrupamento: sql.Composable, colunas: sql.Composable) -> sql.Composed:
    """Agrega as linhas do nó atual pelo próximo segmento do caminho (%(prox)s)."""
    return sql.SQL("""
        SELECT segmento, {colunas}
            mode() WITHIN GROUP (ORDER BY rotulos[%(prox)s]) AS rotulo,
            bool_or(cardinality(caminho) > %(prox)s) AS tem_filhos,
            {agregados}
        FROM (SELECT *, caminho[%(prox)s] AS segmento FROM preco_analise {where}) s
        WHERE segmento IS NOT NULL
        GROUP BY {agrupamento}
    """).format(colunas=colunas, agregados=AGREGADOS, where=where, agrupamento=agrupamento)


@rotas.get("/lojas/{loja_id}/nos")
async def nos_da_loja(
    loja_id: int, f: Filtros = Depends(filtros), conn: psycopg.AsyncConnection = Depends(conexao)
) -> dict[str, Any]:
    """Subcategorias do nó `caminho` numa loja e quantos produtos estão diretamente no nó."""
    where, params = f.where(loja_id=loja_id)
    params["prox"] = len(f.caminho) + 1
    filhos = await _todas(conn, _filhos(where, sql.SQL("segmento"), sql.SQL("")), params)
    where_diretos, _ = f.where(condicoes=[sql.SQL("cardinality(caminho) = %(nivel_atual)s")], loja_id=loja_id)
    cur = await conn.execute(
        sql.SQL("SELECT count(*) AS n FROM preco_analise {where}").format(where=where_diretos),
        {**params, "nivel_atual": len(f.caminho)},
    )
    diretos = (await cur.fetchone())["n"]
    return {
        "filhos": [
            {
                "caminho": [*f.caminho, linha["segmento"]],
                "rotulo": linha["rotulo"],
                "tem_filhos": linha["tem_filhos"],
                "estatisticas": estatisticas(linha),
            }
            for linha in sorted(filhos, key=lambda linha: linha["segmento"])
        ],
        "produtos_diretos": diretos,
    }


COLUNAS_ORDENAVEIS = {
    "nome": "nome", "marca": "marca", "loja": "loja", "categoria": "categoria", "preco": "preco",
    "preco_regular": "preco_regular", "desconto": "desconto", "z": "z",
}


@rotas.get("/produtos")
async def produtos(
    f: Filtros = Depends(filtros),
    exato: bool = Query(False, description="só produtos cujo caminho termina exatamente no nó (sem subcategorias)"),
    ordenar: Literal["nome", "marca", "loja", "categoria", "preco", "preco_regular", "desconto", "z"] = "nome",
    direcao: Literal["asc", "desc"] = "asc",
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(100, ge=1, le=1000),
    conn: psycopg.AsyncConnection = Depends(conexao),
) -> dict[str, Any]:
    """Produtos paginados. `z` é o desvio do preço em relação à média da mesma loja no conjunto filtrado."""
    where, params = f.where(condicoes=[sql.SQL("cardinality(caminho) = %(nivel_exato)s")] if exato else [])
    params["nivel_exato"] = len(f.caminho)

    cur = await conn.execute(sql.SQL("SELECT {agregados} FROM preco_analise {where}").format(
        agregados=AGREGADOS, where=where
    ), params)
    total = await cur.fetchone()

    ordem = sql.SQL("{} {} NULLS LAST, produto_id, loja_id").format(
        sql.Identifier(COLUNAS_ORDENAVEIS[ordenar]), sql.SQL(direcao.upper())
    )
    itens = await _todas(conn, sql.SQL("""
        SELECT produto_id, loja_id, loja, rede, rede_nome, sku, ean, nome, marca, categoria, rotulos,
            preco, preco_regular, em_promocao, desconto, disponivel, coletado_em, url, imagem_url,
            round(((preco - avg(preco) OVER w) / nullif(stddev_samp(preco) OVER w, 0))::numeric, 2) AS z
        FROM preco_analise {where}
        WINDOW w AS (PARTITION BY loja_id)
        ORDER BY {ordem}
        LIMIT %(limite)s OFFSET %(deslocamento)s
    """).format(where=where, ordem=ordem), {**params, "limite": tamanho, "deslocamento": (pagina - 1) * tamanho})
    return {"itens": [_sem_decimal(item) for item in itens], "total_itens": total["n"], "total": estatisticas(total)}


@rotas.get("/categorias/arvore")
async def arvore(f: Filtros = Depends(filtros), conn: psycopg.AsyncConnection = Depends(conexao)) -> list[dict]:
    """Todos os nós de categoria (lista plana; o front monta a árvore pelo `caminho`)."""
    where, params = f.where(sem_caminho=True)
    return await _todas(conn, sql.SQL("""
        SELECT caminho[1:i] AS caminho, mode() WITHIN GROUP (ORDER BY rotulos[i]) AS rotulo,
            count(*) AS n, count(DISTINCT loja_id) AS lojas
        FROM preco_analise CROSS JOIN LATERAL generate_series(1, cardinality(caminho)) AS i
        {where}
        GROUP BY caminho[1:i]
        ORDER BY caminho[1:i]
    """).format(where=where), params)


def _por_loja(linhas: list[dict]) -> list[dict]:
    """Linhas de um GROUPING SETS (loja, todas) no formato da API, com "Todas as lojas" por último."""
    saida = [
        {
            "loja_id": None if linha["todas"] else linha["loja_id"],
            "loja": "Todas as lojas" if linha["todas"] else linha["loja"],
            "rede": None if linha["todas"] else linha["rede"],
            "estatisticas": estatisticas(linha),
        }
        for linha in linhas
    ]
    return sorted(saida, key=lambda linha: (linha["loja_id"] is None, linha["loja"]))


@rotas.get("/categorias/dispersao")
async def dispersao(f: Filtros = Depends(filtros), conn: psycopg.AsyncConnection = Depends(conexao)) -> dict[str, Any]:
    """Dispersão do nó `caminho` e de cada subcategoria, por loja e com uma linha "Todas as lojas"."""
    where, params = f.where()
    no = await _todas(conn, sql.SQL("""
        SELECT loja_id, loja, rede, GROUPING(loja_id) = 1 AS todas, {agregados}
        FROM preco_analise {where}
        GROUP BY GROUPING SETS ((loja_id, loja, rede), ())
    """).format(agregados=AGREGADOS, where=where), params)

    params["prox"] = len(f.caminho) + 1
    filhos = await _todas(conn, _filhos(
        where,
        sql.SQL("GROUPING SETS ((segmento, loja_id, loja, rede), (segmento))"),
        sql.SQL("loja_id, loja, rede, GROUPING(loja_id) = 1 AS todas,"),
    ), params)

    grupos: dict[str, list[dict]] = {}
    for linha in filhos:
        grupos.setdefault(linha["segmento"], []).append(linha)
    subcategorias = []
    for segmento, linhas in sorted(grupos.items()):
        todas = next(linha for linha in linhas if linha["todas"])
        subcategorias.append({
            "caminho": [*f.caminho, segmento],
            "rotulo": todas["rotulo"],
            "tem_filhos": todas["tem_filhos"],
            "lojas": _por_loja(linhas),
        })

    rotulos = await _todas(conn, sql.SQL("""
        SELECT i, mode() WITHIN GROUP (ORDER BY rotulos[i]) AS rotulo
        FROM preco_analise CROSS JOIN generate_series(1, %(nivel_rotulo)s) AS i
        {where}
        GROUP BY i ORDER BY i
    """).format(where=where), {**params, "nivel_rotulo": len(f.caminho)}) if f.caminho else []
    return {
        "caminho": f.caminho,
        "rotulos": [linha["rotulo"] for linha in rotulos],
        "lojas": _por_loja(no) if no and no[0]["n"] else [],
        "subcategorias": subcategorias,
    }


@rotas.get("/categorias/histograma")
async def histograma(
    f: Filtros = Depends(filtros),
    faixas: int = Query(30, ge=2, le=200),
    conn: psycopg.AsyncConnection = Depends(conexao),
) -> dict[str, Any]:
    """Histograma do preço por loja. As faixas vão do mínimo ao percentil 99; acima dele vira uma faixa final."""
    where, params = f.where()
    cur = await conn.execute(sql.SQL("""
        SELECT min(preco) AS minimo, max(preco) AS maximo,
            percentile_cont(0.99) WITHIN GROUP (ORDER BY preco)::numeric AS p99
        FROM preco_analise {where}
    """).format(where=where), params)
    limites = await cur.fetchone()
    if limites["minimo"] is None:
        return {"faixas": [], "lojas": []}

    inicio, fim = limites["minimo"], limites["p99"]
    if fim <= inicio:
        fim = limites["maximo"]
    if fim <= inicio:  # todos os preços iguais
        fim = inicio + 1
    largura = (fim - inicio) / faixas
    transbordo = limites["maximo"] > fim

    contagens = await _todas(conn, sql.SQL("""
        SELECT loja_id, least(width_bucket(preco, %(inicio)s, %(fim)s, %(faixas)s), %(ultima)s) AS faixa,
            count(*) AS n
        FROM preco_analise {where}
        GROUP BY 1, 2
    """).format(where=where), {
        **params, "inicio": inicio, "fim": fim, "faixas": faixas, "ultima": faixas + 1 if transbordo else faixas,
    })
    lojas = await _todas(conn, sql.SQL("""
        SELECT loja_id, loja, rede, {agregados} FROM preco_analise {where} GROUP BY 1, 2, 3 ORDER BY loja
    """).format(agregados=AGREGADOS, where=where), params)

    total_faixas = faixas + 1 if transbordo else faixas
    saida = [
        {
            "inicio": round(float(inicio + largura * i), 2),
            "fim": round(float(inicio + largura * (i + 1)), 2) if i < faixas else round(float(limites["maximo"]), 2),
            "transbordo": i >= faixas,
            "contagens": {},
        }
        for i in range(total_faixas)
    ]
    for linha in contagens:
        saida[linha["faixa"] - 1]["contagens"][str(linha["loja_id"])] = linha["n"]
    return {
        "faixas": saida,
        "lojas": [{"loja_id": l["loja_id"], "loja": l["loja"], "rede": l["rede"], "estatisticas": estatisticas(l)} for l in lojas],
    }


@rotas.get("/{resto:path}", include_in_schema=False)
async def nao_encontrado(resto: str) -> None:
    raise HTTPException(404, f"rota inexistente: /api/{resto}")
