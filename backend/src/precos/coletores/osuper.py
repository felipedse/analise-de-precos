"""Coletor para lojas da plataforma Osuper (Koch, Fort Atacadista).

A busca de produtos da plataforma fica atrás de proteção anti-bot, então o
coletor não a usa. Em vez disso:

1. lista as lojas pela API GraphQL da loja (`onlineStores`) e filtra pela UF;
2. obtém os ids de todos os produtos pelo sitemap público do site;
3. consulta preço e estoque por loja na API GraphQL, 50 produtos por
   requisição (aliases GraphQL).
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator
from typing import Any

from precos.coletores.base import Coletor, em_lotes
from precos.modelos import Loja, Oferta, decimal_ou_none

log = logging.getLogger(__name__)

PRODUTOS_POR_CONSULTA = 50
CONSULTAS_SIMULTANEAS = 4

CAMPOS_PRODUTO = """
    id name slug saleUnit contentUnit content
    brand { name }
    image { thumborized(width: 400, height: 400, fitIn: true) }
    pricing(storeId: $storeId) { price promotion promotionalPrice }
    quantity(storeId: $storeId) { inStock }
"""

CONSULTA_LOJAS = """
query Lojas($storeId: ID!) {
  publicViewer(storeId: $storeId) {
    onlineStores { id name slug webOnline fullAddress { city state } }
  }
}
"""

RE_PRODUTO = re.compile(r"/produtos/(\d+)/")
NS_SITEMAP = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class ColetorOsuper(Coletor):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.api: str = self.rede.opcoes["api"]
        self.uf: str = self.rede.opcoes.get("uf", "SC")
        self._sessao = str(uuid.uuid4())
        self._lojas: list[Loja] | None = None

    async def lojas(self) -> list[Loja]:
        if self._lojas is None:
            dados = await self._graphql(CONSULTA_LOJAS, {"storeId": self.rede.opcoes["loja_referencia"]})
            self._lojas = lojas_da_resposta(dados, self.uf, self.rede.opcoes.get("lojas"))
            log.info("%s: %d lojas em %s", self.rede.slug, len(self._lojas), self.uf)
        return self._lojas

    async def coletar(self, limite: int | None = None) -> AsyncIterator[list[Oferta]]:
        ids = await self.ids_do_sitemap()
        if limite is not None:
            ids = ids[:limite]
        log.info("%s: %d produtos no sitemap", self.rede.slug, len(ids))

        for loja in await self.lojas():
            lotes = list(em_lotes(ids, PRODUTOS_POR_CONSULTA))
            for grupo in em_lotes(lotes, CONSULTAS_SIMULTANEAS):
                resultados = await asyncio.gather(
                    *(self._consultar_produtos(loja, lote) for lote in grupo), return_exceptions=True
                )
                ofertas: list[Oferta] = []
                for resultado in resultados:
                    if isinstance(resultado, BaseException):
                        self.erros += 1
                        log.error("%s: falha na loja %s: %s", self.rede.slug, loja.codigo, resultado)
                    else:
                        ofertas.extend(resultado)
                if ofertas:
                    yield ofertas

    async def ids_do_sitemap(self) -> list[str]:
        ids: dict[str, None] = {}  # dict para manter a ordem sem repetir
        pendentes = [f"{self.rede.site}/sitemap.xml"]
        while pendentes:
            resp = await self.http.get(pendentes.pop())
            raiz = ET.fromstring(resp.content)
            if raiz.tag == f"{NS_SITEMAP}sitemapindex":
                pendentes.extend(loc.text.strip() for loc in raiz.iter(f"{NS_SITEMAP}loc") if loc.text)
                continue
            for loc in raiz.iter(f"{NS_SITEMAP}loc"):
                if loc.text and (m := RE_PRODUTO.search(loc.text)):
                    ids[m.group(1)] = None
        return list(ids)

    async def _consultar_produtos(self, loja: Loja, ids: list[str]) -> list[Oferta]:
        dados = await self._graphql(consulta_produtos(ids), {"storeId": loja.codigo})
        visor = dados.get("publicViewer") or {}
        return [
            oferta
            for produto in visor.values()
            if isinstance(produto, dict) and (oferta := self.oferta_do_produto(produto, loja.codigo))
        ]

    def oferta_do_produto(self, produto: dict[str, Any], loja_codigo: str) -> Oferta | None:
        precos = produto.get("pricing") or {}
        normal = decimal_ou_none(precos.get("price"))
        promocional = decimal_ou_none(precos.get("promotionalPrice"))
        if not normal:  # produto sem preço nesta loja
            return None
        em_promocao = bool(precos.get("promotion") and promocional and promocional < normal)
        estoque = decimal_ou_none((produto.get("quantity") or {}).get("inStock"))
        conteudo = produto.get("content")

        return Oferta(
            loja_codigo=loja_codigo,
            sku=str(produto["id"]),
            nome=produto["name"].strip(),
            preco=promocional if em_promocao else normal,
            preco_regular=normal,
            em_promocao=em_promocao,
            disponivel=estoque is None or estoque > 0,
            estoque=estoque,
            marca=(produto.get("brand") or {}).get("name"),
            unidade=(produto.get("saleUnit") or "").lower() or None,
            fator_unidade=decimal_ou_none(conteudo),
            url=f"{self.rede.site}/produtos/{produto['id']}/{produto.get('slug') or ''}",
            imagem_url=(produto.get("image") or {}).get("thumborized"),
        )

    async def _graphql(self, consulta: str, variaveis: dict[str, Any]) -> dict[str, Any]:
        resp = await self.http.post(
            self.api,
            json={"query": consulta, "variables": variaveis},
            headers={
                "Accept": "application/json",
                "Origin": self.rede.site,
                # A API recusa requisições sem estes cabeçalhos do cliente web.
                "versioning": "Apollo Client Frontend Production",
                "sessionid": self._sessao,
            },
        )
        corpo = resp.json()
        if corpo.get("errors") and not corpo.get("data"):
            raise RuntimeError(f"erro GraphQL: {corpo['errors'][0].get('message')}")
        if corpo.get("errors"):
            log.debug("%s: erros parciais GraphQL: %s", self.rede.slug, corpo["errors"][:3])
        return corpo.get("data") or {}


def consulta_produtos(ids: list[str]) -> str:
    """Monta uma consulta GraphQL com um alias por produto."""
    campos = []
    for i, id_ in enumerate(ids):
        if not id_.isdigit():
            raise ValueError(f"id de produto inválido: {id_!r}")
        campos.append(f'p{i}: product(id: "{id_}", storeId: $storeId) {{ {CAMPOS_PRODUTO} }}')
    return "query Produtos($storeId: ID!) { publicViewer(storeId: $storeId) { id " + " ".join(campos) + " } }"


def lojas_da_resposta(dados: dict[str, Any], uf: str, somente: list[str] | None = None) -> list[Loja]:
    lojas = []
    for loja in (dados.get("publicViewer") or {}).get("onlineStores") or []:
        endereco = loja.get("fullAddress") or {}
        if endereco.get("state") != uf or not loja.get("webOnline"):
            continue
        if somente and loja["id"] not in somente:
            continue
        cidade = endereco.get("city")
        nome = loja.get("name") or loja["slug"]
        if cidade and cidade.lower() not in nome.lower():
            # Nome genérico (ex.: "Fort Atacadista"); a cidade pode ter mais de uma loja.
            nome = f"{nome} - {cidade} ({loja['slug']})"
        lojas.append(Loja(codigo=str(loja["id"]), nome=nome, cidade=cidade, uf=uf))
    return lojas
