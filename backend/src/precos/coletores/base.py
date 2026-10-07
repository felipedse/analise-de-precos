from __future__ import annotations

import abc
from collections.abc import AsyncIterator, Iterable, Iterator
from itertools import islice
from typing import TypeVar

from precos.http import ClienteHttp
from precos.modelos import Loja, Oferta, Rede

T = TypeVar("T")


class Coletor(abc.ABC):
    """Interface de um coletor de preços para uma plataforma de e-commerce."""

    def __init__(self, rede: Rede, http: ClienteHttp) -> None:
        self.rede = rede
        self.http = http
        self.erros = 0

    @abc.abstractmethod
    async def lojas(self) -> list[Loja]:
        """Lojas cujos preços serão coletados. Chamado antes de `coletar`."""

    @abc.abstractmethod
    def coletar(self, limite: int | None = None) -> AsyncIterator[list[Oferta]]:
        """Gera lotes de ofertas. `limite` restringe o número de produtos (para testes)."""


def em_lotes(itens: Iterable[T], tamanho: int) -> Iterator[list[T]]:
    it = iter(itens)
    while lote := list(islice(it, tamanho)):
        yield lote
