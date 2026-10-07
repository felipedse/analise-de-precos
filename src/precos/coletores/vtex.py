"""Coletor para lojas VTEX (Angeloni, Giassi, Bistek).

Usa a API pública de catálogo, percorrendo a árvore de categorias
(`fq=C:/id/`). A busca textual (`ft=`) não é usada: alguns sites a proíbem
no robots.txt e ela não serve para varrer o catálogo inteiro.

A API só pagina até o item 2500 de cada consulta. Categorias maiores que
isso são divididas nas subcategorias; se uma folha ainda passar do limite,
ela é lida também na ordem inversa de preço para cobrir até 5000 itens.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

from precos.coletores.base import Coletor, em_lotes
from precos.modelos import Loja, Oferta, decimal_ou_none

log = logging.getLogger(__name__)

POR_PAGINA = 50
LIMITE_PAGINACAO = 2500
PAGINAS_SIMULTANEAS = 8
LOJA_ONLINE = "online"


class ColetorVtex(Coletor):
    async def lojas(self) -> list[Loja]:
        # Sem regionalização: o preço do canal de venda padrão vale para a loja online.
        return [Loja(LOJA_ONLINE, f"{self.rede.nome} (loja online)", uf="SC")]

    async def coletar(self, limite: int | None = None) -> AsyncIterator[list[Oferta]]:
        resp = await self.http.get(f"{self.rede.site}/api/catalog_system/pub/category/tree/10")
        arvore = resp.json()
        vistos: set[str] = set()

        for categoria in arvore:
            async for produtos in self._produtos_da_categoria(categoria, f"/{categoria['id']}/"):
                novas = []
                for oferta in (o for p in produtos for o in self.ofertas_do_produto(p)):
                    if limite is not None and len(vistos) >= limite:
                        break
                    if oferta.sku not in vistos:  # o mesmo produto aparece em várias categorias
                        vistos.add(oferta.sku)
                        novas.append(oferta)
                if novas:
                    yield novas
                if limite is not None and len(vistos) >= limite:
                    return

    async def _produtos_da_categoria(
        self, categoria: dict[str, Any], caminho: str
    ) -> AsyncIterator[list[dict[str, Any]]]:
        try:
            primeira, total = await self._buscar(caminho, 0)
        except Exception as e:
            self.erros += 1
            log.error("%s: categoria %s (%s) ignorada: %s", self.rede.slug, categoria["name"], caminho, e)
            return
        filhos = categoria.get("children") or []

        if total > LIMITE_PAGINACAO and filhos:
            for filho in filhos:
                async for produtos in self._produtos_da_categoria(filho, f"{caminho}{filho['id']}/"):
                    yield produtos
            return

        log.debug("%s: categoria %s (%s) com %d produtos", self.rede.slug, categoria["name"], caminho, total)
        yield primeira
        async for produtos in self._paginas(caminho, range(POR_PAGINA, min(total, LIMITE_PAGINACAO), POR_PAGINA)):
            yield produtos

        if total > LIMITE_PAGINACAO:
            restante = min(total - LIMITE_PAGINACAO, LIMITE_PAGINACAO)
            log.warning(
                "%s: categoria %s tem %d produtos (> %d); lendo mais %d em ordem inversa de preço",
                self.rede.slug, categoria["name"], total, LIMITE_PAGINACAO, restante,
            )
            async for produtos in self._paginas(caminho, range(0, restante, POR_PAGINA), "OrderByPriceDESC"):
                yield produtos

    async def _paginas(
        self, caminho: str, inicios: range, ordem: str | None = None
    ) -> AsyncIterator[list[dict[str, Any]]]:
        for grupo in em_lotes(inicios, PAGINAS_SIMULTANEAS):
            resultados = await asyncio.gather(
                *(self._buscar(caminho, inicio, ordem) for inicio in grupo), return_exceptions=True
            )
            for resultado in resultados:
                if isinstance(resultado, BaseException):
                    self.erros += 1
                    log.error("%s: falha ao ler página de %s: %s", self.rede.slug, caminho, resultado)
                    continue
                yield resultado[0]

    async def _buscar(
        self, caminho: str, inicio: int, ordem: str | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        params = {"fq": f"C:{caminho}", "_from": inicio, "_to": inicio + POR_PAGINA - 1}
        if ordem:
            params["O"] = ordem
        resp = await self.http.get(f"{self.rede.site}/api/catalog_system/pub/products/search", params=params)
        return resp.json(), total_do_cabecalho(resp.headers.get("resources"))

    def ofertas_do_produto(self, produto: dict[str, Any]) -> list[Oferta]:
        """Converte um produto da API de catálogo em uma oferta por SKU."""
        itens = produto.get("items") or []
        categorias = produto.get("categories") or []
        categoria = " > ".join(c for c in categorias[0].split("/") if c) if categorias else None
        url = f"{self.rede.site}/{produto['linkText']}/p" if produto.get("linkText") else None

        ofertas = []
        for item in itens:
            vendedores = item.get("sellers") or []
            vendedor = next((v for v in vendedores if v.get("sellerDefault")), vendedores[0] if vendedores else None)
            if not vendedor:
                continue
            oferta = vendedor.get("commertialOffer") or {}
            preco = decimal_ou_none(oferta.get("Price"))
            if not preco:  # VTEX devolve 0 para itens indisponíveis
                continue
            regular = decimal_ou_none(oferta.get("ListPrice")) or decimal_ou_none(oferta.get("PriceWithoutDiscount"))
            imagens = item.get("images") or []
            estoque = oferta.get("AvailableQuantity")
            nome = produto["productName"]
            if len(itens) > 1:  # produto com variações: usa o nome do SKU
                nome = item.get("nameComplete") or item.get("name") or nome

            ofertas.append(
                Oferta(
                    loja_codigo=LOJA_ONLINE,
                    sku=str(item["itemId"]),
                    nome=nome.strip(),
                    preco=preco,
                    preco_regular=regular,
                    em_promocao=bool(regular and regular > preco),
                    disponivel=bool(oferta.get("IsAvailable", True)),
                    # VTEX costuma devolver 99999 como "estoque ilimitado"; não é um número real.
                    estoque=Decimal(estoque) if isinstance(estoque, int) and estoque < 99999 else None,
                    marca=produto.get("brand") or None,
                    ean=(item.get("ean") or "").strip() or None,
                    categoria=categoria,
                    unidade=item.get("measurementUnit"),
                    fator_unidade=decimal_ou_none(item.get("unitMultiplier")),
                    url=url,
                    imagem_url=imagens[0].get("imageUrl") if imagens else None,
                )
            )
        return ofertas


def total_do_cabecalho(resources: str | None) -> int:
    """Lê o total do cabeçalho `resources: 0-49/1234`."""
    m = re.search(r"/(\d+)$", resources or "")
    return int(m.group(1)) if m else 0
