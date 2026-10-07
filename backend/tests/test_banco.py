import pytest


@pytest.mark.parametrize(
    ("categoria", "esperado"),
    [
        ("Mercearia > Arroz e Feijão", ["mercearia", "arroz e feijao"]),
        ("  MERCEARIA  >  Açúcar   Refinado ", ["mercearia", "acucar refinado"]),
        ("Bebidas>>Água", ["bebidas", "agua"]),
        (None, ["sem categoria"]),
        ("", ["sem categoria"]),
    ],
)
def test_normalizar_categoria(banco, categoria, esperado):
    (caminho,) = banco.execute("SELECT normalizar_categoria(%s)", (categoria,)).fetchone()
    assert caminho == esperado


def test_segmentos_categoria_preserva_o_texto(banco):
    (rotulos,) = banco.execute("SELECT segmentos_categoria('Mercearia >  Arroz e  Feijão')").fetchone()
    assert rotulos == ["Mercearia", "Arroz e Feijão"]
