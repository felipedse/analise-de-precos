from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class Rede:
    slug: str
    nome: str
    plataforma: str  # nome do coletor em precos.coletores
    site: str
    opcoes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Loja:
    codigo: str
    nome: str
    cidade: str | None = None
    uf: str | None = None


@dataclass
class Oferta:
    """Preço de um produto em uma loja, como lido do site."""

    loja_codigo: str
    sku: str
    nome: str
    preco: Decimal
    preco_regular: Decimal | None = None
    em_promocao: bool = False
    disponivel: bool = True
    estoque: Decimal | None = None
    marca: str | None = None
    ean: str | None = None
    categoria: str | None = None
    unidade: str | None = None
    fator_unidade: Decimal | None = None
    url: str | None = None
    imagem_url: str | None = None


def decimal_ou_none(valor: Any) -> Decimal | None:
    if valor is None or valor == "":
        return None
    try:
        return Decimal(str(valor))
    except ArithmeticError:
        return None
