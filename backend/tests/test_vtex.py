from decimal import Decimal

from precos.coletores.vtex import ColetorVtex, total_do_cabecalho
from precos.redes import REDES


def produto(**sobrescritas):
    base = {
        "productId": "100",
        "productName": "Arroz Parboilizado URBANO 1kg",
        "brand": "Urbano",
        "linkText": "arroz-parboilizado-urbano-1kg",
        "categories": ["/Mercearia/Arroz e Feijão/Arroz/", "/Mercearia/Arroz e Feijão/", "/Mercearia/"],
        "items": [
            {
                "itemId": "200",
                "name": "Arroz Parboilizado URBANO 1kg",
                "ean": "7896038306053",
                "measurementUnit": "un",
                "unitMultiplier": 1.0,
                "images": [{"imageUrl": "https://img/arroz.jpg"}],
                "sellers": [
                    {
                        "sellerId": "1",
                        "sellerDefault": True,
                        "commertialOffer": {
                            "Price": 3.59,
                            "ListPrice": 4.69,
                            "AvailableQuantity": 99999,
                            "IsAvailable": True,
                        },
                    }
                ],
            }
        ],
    }
    base.update(sobrescritas)
    return base


def coletor():
    return ColetorVtex(REDES["angeloni"], http=None)


def test_converte_produto_em_oferta():
    [o] = coletor().ofertas_do_produto(produto())
    assert o.sku == "200"
    assert o.nome == "Arroz Parboilizado URBANO 1kg"
    assert o.preco == Decimal("3.59")
    assert o.preco_regular == Decimal("4.69")
    assert o.em_promocao
    assert o.ean == "7896038306053"
    assert o.categoria == "Mercearia > Arroz e Feijão > Arroz"
    assert o.url == "https://super.angeloni.com.br/arroz-parboilizado-urbano-1kg/p"
    assert o.estoque is None  # 99999 = estoque "ilimitado"
    assert o.loja_codigo == "online"


def test_ignora_item_sem_preco():
    p = produto()
    p["items"][0]["sellers"][0]["commertialOffer"].update(Price=0, IsAvailable=False)
    assert coletor().ofertas_do_produto(p) == []


def test_sem_promocao_quando_preco_igual_ao_de_lista():
    p = produto()
    p["items"][0]["sellers"][0]["commertialOffer"]["ListPrice"] = 3.59
    [o] = coletor().ofertas_do_produto(p)
    assert not o.em_promocao


def test_total_do_cabecalho():
    assert total_do_cabecalho("0-49/31107") == 31107
    assert total_do_cabecalho(None) == 0
