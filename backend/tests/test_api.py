import statistics
from decimal import Decimal

import pytest


def precos(banco, where="disponivel", params=()):
    return [float(p) for (p,) in banco.execute(f"SELECT preco FROM preco_analise WHERE {where}", params)]


def confere(estatisticas, valores):
    assert estatisticas["n"] == len(valores)
    assert estatisticas["minimo"] == pytest.approx(min(valores))
    assert estatisticas["maximo"] == pytest.approx(max(valores))
    assert estatisticas["media"] == pytest.approx(statistics.fmean(valores), abs=0.01)
    assert estatisticas["mediana"] == pytest.approx(statistics.median(valores), abs=0.01)
    assert estatisticas["desvio"] == pytest.approx(statistics.stdev(valores), abs=0.01)
    assert estatisticas["faixa_inferior"] == pytest.approx(statistics.fmean(valores) - statistics.stdev(valores), abs=0.02)
    assert estatisticas["faixa_superior"] == pytest.approx(statistics.fmean(valores) + statistics.stdev(valores), abs=0.02)


def test_meta(cliente):
    meta = cliente.get("/api/meta").json()
    assert {r["slug"] for r in meta["redes"]} == {"giassi", "angeloni"}
    assert len(meta["lojas"]) == 2
    assert meta["marcas"][0]["n"] >= meta["marcas"][-1]["n"]


def test_lojas_e_total(cliente, banco):
    dados = cliente.get("/api/lojas").json()
    assert len(dados["linhas"]) == 2
    confere(dados["total"], precos(banco))
    assert sum(l["estatisticas"]["n"] for l in dados["linhas"]) == dados["total"]["n"]
    for linha in dados["linhas"]:
        confere(linha["estatisticas"], precos(banco, "disponivel AND loja_id = %s", (linha["loja_id"],)))


def test_filtros(cliente, banco):
    so_promo = cliente.get("/api/lojas", params={"promocao": True}).json()["total"]
    assert so_promo["n"] == so_promo["n_promocao"] > 0

    giassi = cliente.get("/api/lojas", params={"rede": "giassi"}).json()
    assert [l["rede"] for l in giassi["linhas"]] == ["giassi"]

    faixa = cliente.get("/api/lojas", params={"preco_min": 10, "preco_max": 20}).json()["total"]
    assert faixa["minimo"] >= 10 and faixa["maximo"] <= 20
    assert faixa["n"] == len(precos(banco, "disponivel AND preco BETWEEN 10 AND 20"))

    # Busca ignora acento e caixa e exige todas as palavras.
    itens = cliente.get("/api/produtos", params={"q": "ACUCAR refinado", "tamanho": 1000}).json()["itens"]
    assert itens
    assert all("refinado" in i["nome"].lower() for i in itens)


def test_drill_down_por_loja(cliente):
    loja = cliente.get("/api/lojas").json()["linhas"][0]
    raiz = cliente.get(f"/api/lojas/{loja['loja_id']}/nos").json()
    assert sum(f["estatisticas"]["n"] for f in raiz["filhos"]) + raiz["produtos_diretos"] == loja["estatisticas"]["n"]

    departamento = next(f for f in raiz["filhos"] if f["tem_filhos"])
    abaixo = cliente.get(
        f"/api/lojas/{loja['loja_id']}/nos", params={"caminho": departamento["caminho"]}
    ).json()
    assert all(f["caminho"][:1] == departamento["caminho"] for f in abaixo["filhos"])
    total = sum(f["estatisticas"]["n"] for f in abaixo["filhos"]) + abaixo["produtos_diretos"]
    assert total == departamento["estatisticas"]["n"]

    diretos = cliente.get("/api/produtos", params={
        "loja": loja["loja_id"], "caminho": departamento["caminho"], "exato": True,
    }).json()
    assert diretos["total_itens"] == abaixo["produtos_diretos"]


def test_produtos_paginacao_e_ordenacao(cliente):
    params = {"caminho": "mercearia", "ordenar": "preco", "direcao": "desc", "tamanho": 50}
    p1 = cliente.get("/api/produtos", params=params).json()
    p2 = cliente.get("/api/produtos", params={**params, "pagina": 2}).json()
    valores = [i["preco"] for i in p1["itens"] + p2["itens"]]
    assert valores == sorted(valores, reverse=True)
    assert p1["total_itens"] == p1["total"]["n"] > 100
    chaves = {(i["produto_id"], i["loja_id"]) for i in p1["itens"]}
    assert not chaves & {(i["produto_id"], i["loja_id"]) for i in p2["itens"]}
    assert all(isinstance(i["preco"], float) for i in p1["itens"])


def test_ordenacao_invalida(cliente):
    assert cliente.get("/api/produtos", params={"ordenar": "preco; DROP TABLE preco"}).status_code == 422


def test_arvore(cliente):
    nos = cliente.get("/api/categorias/arvore").json()
    caminhos = {tuple(n["caminho"]) for n in nos}
    assert all(c[:-1] in caminhos for c in caminhos if len(c) > 1)  # todo nó tem o pai
    assert ("mercearia",) in caminhos


def test_dispersao(cliente, banco):
    dados = cliente.get("/api/categorias/dispersao", params={"caminho": "mercearia"}).json()
    assert dados["rotulos"] == ["Mercearia"]
    todas = next(l for l in dados["lojas"] if l["loja_id"] is None)
    confere(todas["estatisticas"], precos(banco, "disponivel AND caminho[1] = 'mercearia'"))

    for sub in dados["subcategorias"]:
        assert sub["caminho"][0] == "mercearia"
        lojas = [l for l in sub["lojas"] if l["loja_id"] is not None]
        todas_sub = next(l for l in sub["lojas"] if l["loja_id"] is None)
        assert sum(l["estatisticas"]["n"] for l in lojas) == todas_sub["estatisticas"]["n"]

    sub = max(dados["subcategorias"], key=lambda s: next(l for l in s["lojas"] if l["loja_id"] is None)["estatisticas"]["n"])
    loja = next(l for l in sub["lojas"] if l["loja_id"] is not None)
    confere(loja["estatisticas"], precos(
        banco, "disponivel AND caminho[1:2] = %s AND loja_id = %s", (sub["caminho"], loja["loja_id"])
    ))


def test_histograma(cliente):
    dados = cliente.get("/api/categorias/histograma", params={"caminho": "mercearia", "faixas": 20}).json()
    n_por_loja = {str(l["loja_id"]): l["estatisticas"]["n"] for l in dados["lojas"]}
    for loja_id, n in n_por_loja.items():
        assert sum(f["contagens"].get(loja_id, 0) for f in dados["faixas"]) == n
    normais = [f for f in dados["faixas"] if not f["transbordo"]]
    assert len(normais) == 20
    assert all(a["fim"] == pytest.approx(b["inicio"]) for a, b in zip(normais, normais[1:]))


def test_histograma_vazio(cliente):
    dados = cliente.get("/api/categorias/histograma", params={"q": "nao-existe-xyz"}).json()
    assert dados == {"faixas": [], "lojas": []}


def test_decimal_do_desconto(cliente):
    item = cliente.get("/api/produtos", params={"promocao": True, "tamanho": 1}).json()["itens"][0]
    assert item["em_promocao"]
    assert Decimal(str(item["desconto"])) == (
        (Decimal(str(item["preco_regular"])) - Decimal(str(item["preco"]))) / Decimal(str(item["preco_regular"]))
    ).quantize(Decimal("0.0001"))
