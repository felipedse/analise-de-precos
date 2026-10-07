"""Estatísticas de preço calculadas no SQL e o formato devolvido pela API."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from psycopg import sql

# Agregados de preço de um grupo de linhas de `preco_analise`.
AGREGADOS = sql.SQL("""
    count(*)                                                AS n,
    count(*) FILTER (WHERE em_promocao)                     AS n_promocao,
    avg(preco)                                              AS media,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY preco)      AS mediana,
    min(preco)                                              AS minimo,
    max(preco)                                              AS maximo,
    stddev_samp(preco)                                      AS desvio,
    avg(desconto) FILTER (WHERE em_promocao)                AS desconto_medio
""")

CAMPOS = ("n", "n_promocao", "media", "mediana", "minimo", "maximo", "desvio", "desconto_medio")


def _num(valor: Any, casas: int = 2) -> float | None:
    return None if valor is None else round(float(valor), casas)


def estatisticas(linha: dict[str, Any]) -> dict[str, Any]:
    """Converte os agregados de uma linha no formato da API, com os campos derivados."""
    n = linha.get("n") or 0
    media = linha.get("media")
    desvio = linha.get("desvio")  # nulo quando há um item só
    return {
        "n": n,
        "n_promocao": linha.get("n_promocao") or 0,
        "pct_promocao": _num((linha.get("n_promocao") or 0) / n, 4) if n else None,
        "media": _num(media),
        "mediana": _num(linha.get("mediana")),
        "minimo": _num(linha.get("minimo")),
        "maximo": _num(linha.get("maximo")),
        "desvio": _num(desvio),
        "faixa_inferior": _num(Decimal(media) - Decimal(desvio)) if media is not None and desvio is not None else None,
        "faixa_superior": _num(Decimal(media) + Decimal(desvio)) if media is not None and desvio is not None else None,
        "desconto_medio": _num(linha.get("desconto_medio"), 4),
    }


def sem_estatisticas(linha: dict[str, Any]) -> dict[str, Any]:
    """Os demais campos da linha (sem os agregados)."""
    return {k: v for k, v in linha.items() if k not in CAMPOS}
