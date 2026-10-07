"""Filtros comuns a todos os endpoints, traduzidos para um WHERE parametrizado sobre `preco_analise`."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from fastapi import Query
from psycopg import sql


@dataclass
class Filtros:
    q: str | None = None
    rede: list[str] = field(default_factory=list)
    loja: list[int] = field(default_factory=list)
    marca: list[str] = field(default_factory=list)
    preco_min: Decimal | None = None
    preco_max: Decimal | None = None
    promocao: bool = False
    indisponiveis: bool = False
    caminho: list[str] = field(default_factory=list)

    def where(
        self, *, sem_caminho: bool = False, condicoes: list[sql.Composable] | None = None, **extras: Any
    ) -> tuple[sql.Composable, dict[str, Any]]:
        """Monta `WHERE ...` e os parâmetros.

        `condicoes` acrescenta trechos SQL prontos; `extras`, igualdades (ex.: loja_id=3).
        """
        condicoes = list(condicoes or [])
        params: dict[str, Any] = {}

        if self.q:
            for i, palavra in enumerate(self.q.split()):
                condicoes.append(sql.SQL(
                    "(busca LIKE '%%' || normalizar_texto({p}) || '%%' OR ean = {p})"
                ).format(p=sql.Placeholder(f"q{i}")))
                params[f"q{i}"] = palavra
        if self.rede:
            condicoes.append(sql.SQL("rede = ANY(%(rede)s)"))
            params["rede"] = self.rede
        if self.loja:
            condicoes.append(sql.SQL("loja_id = ANY(%(loja)s)"))
            params["loja"] = self.loja
        if self.marca:
            condicoes.append(sql.SQL("marca = ANY(%(marca)s)"))
            params["marca"] = self.marca
        if self.preco_min is not None:
            condicoes.append(sql.SQL("preco >= %(preco_min)s"))
            params["preco_min"] = self.preco_min
        if self.preco_max is not None:
            condicoes.append(sql.SQL("preco <= %(preco_max)s"))
            params["preco_max"] = self.preco_max
        if self.promocao:
            condicoes.append(sql.SQL("em_promocao"))
        if not self.indisponiveis:
            condicoes.append(sql.SQL("disponivel"))
        if self.caminho and not sem_caminho:
            condicoes.append(sql.SQL("caminho[1:%(nivel)s] = %(caminho)s::text[]"))
            params["nivel"] = len(self.caminho)
            params["caminho"] = self.caminho
        for coluna, valor in extras.items():
            condicoes.append(sql.SQL("{} = {}").format(sql.Identifier(coluna), sql.Placeholder(f"x_{coluna}")))
            params[f"x_{coluna}"] = valor

        if not condicoes:
            return sql.SQL(""), params
        return sql.SQL("WHERE ") + sql.SQL(" AND ").join(condicoes), params


def filtros(
    q: str | None = Query(None, description="busca em nome/marca (todas as palavras) ou EAN exato"),
    rede: list[str] = Query([], description="slugs das redes"),
    loja: list[int] = Query([], description="ids das lojas"),
    marca: list[str] = Query([], description="marcas"),
    preco_min: Decimal | None = Query(None, ge=0),
    preco_max: Decimal | None = Query(None, ge=0),
    promocao: bool = Query(False, description="só itens em promoção"),
    indisponiveis: bool = Query(False, description="incluir itens indisponíveis"),
    caminho: list[str] = Query([], description="caminho normalizado da categoria, um segmento por parâmetro"),
) -> Filtros:
    return Filtros(q and q.strip() or None, rede, loja, marca, preco_min, preco_max, promocao, indisponiveis, caminho)
