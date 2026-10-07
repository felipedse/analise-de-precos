from precos.coletores.base import Coletor
from precos.coletores.osuper import ColetorOsuper
from precos.coletores.vtex import ColetorVtex
from precos.http import ClienteHttp
from precos.modelos import Rede

COLETORES: dict[str, type[Coletor]] = {
    "vtex": ColetorVtex,
    "osuper": ColetorOsuper,
}


def criar_coletor(rede: Rede, http: ClienteHttp) -> Coletor:
    return COLETORES[rede.plataforma](rede, http)
