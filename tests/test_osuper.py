from decimal import Decimal

import pytest

from precos.coletores.osuper import ColetorOsuper, consulta_produtos, lojas_da_resposta
from precos.redes import REDES


def coletor():
    return ColetorOsuper(REDES["koch"], http=None)


def produto(**pricing):
    return {
        "id": "7069522",
        "name": "Feijão Caldão Preto 1Kg ",
        "slug": "feijao-caldao-preto-1kg",
        "saleUnit": "UN",
        "content": None,
        "brand": {"name": "CALDÃO"},
        "image": {"thumborized": "https://img/feijao.jpg"},
        "pricing": {"price": 6.99, "promotion": False, "promotionalPrice": 0, **pricing},
        "quantity": {"inStock": 270},
    }


def test_oferta_sem_promocao():
    o = coletor().oferta_do_produto(produto(), "1415")
    assert o.sku == "7069522"
    assert o.nome == "Feijão Caldão Preto 1Kg"
    assert o.preco == Decimal("6.99")
    assert not o.em_promocao
    assert o.disponivel
    assert o.unidade == "un"
    assert o.url == "https://www.superkoch.com.br/produtos/7069522/feijao-caldao-preto-1kg"


def test_oferta_em_promocao_usa_preco_promocional():
    o = coletor().oferta_do_produto(produto(promotion=True, promotionalPrice=5.49), "1415")
    assert o.preco == Decimal("5.49")
    assert o.preco_regular == Decimal("6.99")
    assert o.em_promocao


def test_produto_sem_preco_na_loja_e_ignorado():
    assert coletor().oferta_do_produto(produto(price=None), "1415") is None


def test_consulta_produtos_usa_aliases_e_valida_ids():
    q = consulta_produtos(["1", "22"])
    assert 'p0: product(id: "1"' in q and 'p1: product(id: "22"' in q
    with pytest.raises(ValueError):
        consulta_produtos(['1") { id } x: product(id: "2'])


def test_lojas_filtra_uf_e_lojas_offline():
    dados = {
        "publicViewer": {
            "onlineStores": [
                {"id": "1", "name": "Fort Atacadista", "slug": "blumenau", "webOnline": True,
                 "fullAddress": {"city": "Blumenau", "state": "SC"}},
                {"id": "2", "name": "Fort Atacadista", "slug": "canoas", "webOnline": True,
                 "fullAddress": {"city": "Canoas", "state": "RS"}},
                {"id": "3", "name": "Fort Atacadista", "slug": "lages", "webOnline": False,
                 "fullAddress": {"city": "Lages", "state": "SC"}},
            ]
        }
    }
    [loja] = lojas_da_resposta(dados, "SC")
    assert loja.codigo == "1"
    assert loja.nome == "Fort Atacadista - Blumenau (blumenau)"
