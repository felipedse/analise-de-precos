from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from precos import banco
from precos.coletores import criar_coletor
from precos.http import ClienteHttp
from precos.modelos import Oferta, Rede

log = logging.getLogger(__name__)


@dataclass
class Resultado:
    rede: str
    precos: int
    erros: int
    segundos: float
    falha: str | None = None


async def coletar_rede(
    rede: Rede,
    *,
    limite: int | None = None,
    gravar: bool = True,
    concorrencia: int = 4,
    intervalo: float = 0.2,
) -> Resultado:
    """Coleta os preços de uma rede e grava no banco (ou só conta, se `gravar=False`)."""
    inicio = time.monotonic()
    total = 0
    amostra: list[Oferta] = []

    async with ClienteHttp(concorrencia=concorrencia, intervalo=intervalo) as http:
        coletor = criar_coletor(rede, http)
        conn = await banco.conectar() if gravar else None
        gravador = banco.Gravador(conn, rede) if conn else None
        try:
            lojas = await coletor.lojas()
            if gravador:
                await gravador.iniciar(lojas)

            async for ofertas in coletor.coletar(limite=limite):
                if gravador:
                    await gravador.gravar(ofertas)
                elif len(amostra) < 3:
                    amostra.extend(ofertas[: 3 - len(amostra)])
                total += len(ofertas)
                log.info("%s: %d preços coletados", rede.slug, total)

            if gravador:
                await gravador.finalizar("ok", coletor.erros)
        except Exception as e:
            log.exception("%s: coleta interrompida", rede.slug)
            if gravador and gravador.coleta_id:
                await gravador.finalizar("erro", coletor.erros, f"{type(e).__name__}: {e}")
            return Resultado(rede.slug, total, coletor.erros, time.monotonic() - inicio, str(e))
        finally:
            if conn:
                await conn.close()

    for o in amostra:
        log.info("%s: exemplo -> [%s] %s: R$ %s (de R$ %s) ean=%s", rede.slug, o.loja_codigo, o.nome, o.preco,
                 o.preco_regular, o.ean)
    return Resultado(rede.slug, total, coletor.erros, time.monotonic() - inicio)
