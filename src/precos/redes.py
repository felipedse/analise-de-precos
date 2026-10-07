"""Supermercados de SC suportados.

Para adicionar uma rede que já use uma plataforma suportada, basta incluir
uma entrada aqui.
"""

from precos.modelos import Rede

REDES: dict[str, Rede] = {
    r.slug: r
    for r in [
        # --- VTEX: catálogo público, preço único por rede (canal de venda padrão) ---
        Rede("angeloni", "Angeloni", "vtex", "https://super.angeloni.com.br"),
        Rede("giassi", "Giassi", "vtex", "https://www.giassi.com.br"),
        Rede("bistek", "Bistek", "vtex", "https://www.bistek.com.br"),
        # --- Osuper: preço por loja física ---
        Rede(
            "koch",
            "Koch",
            "osuper",
            "https://www.superkoch.com.br",
            {
                "api": "https://api.superkoch.com.br/storefront/graphql",
                "loja_referencia": "1415",  # qualquer loja válida, usada para listar as demais
            },
        ),
        Rede(
            "fort",
            "Fort Atacadista",
            "osuper",
            "https://www.fortatacadista.com.br",
            {
                "api": "https://api.fortatacadista.com.br/storefront/graphql",
                "loja_referencia": "1585",
            },
        ),
    ]
}
