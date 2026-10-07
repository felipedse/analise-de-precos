from __future__ import annotations

import asyncio
import logging
import os
import random

import httpx

log = logging.getLogger(__name__)

USER_AGENT_PADRAO = "Mozilla/5.0 (compatible; precos-sc/0.1)"
STATUS_TEMPORARIOS = {408, 425, 429, 500, 502, 503, 504}


class ClienteHttp:
    """Cliente HTTP educado: limita concorrência, espaça as requisições e
    repete em falhas temporárias com backoff exponencial."""

    def __init__(
        self,
        concorrencia: int = 4,
        intervalo: float = 0.2,
        tentativas: int = 4,
        timeout: float = 30.0,
    ) -> None:
        self._cliente = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": os.environ.get("PRECOS_USER_AGENT", USER_AGENT_PADRAO),
                "Accept-Language": "pt-BR,pt;q=0.9",
            },
        )
        self._semaforo = asyncio.Semaphore(concorrencia)
        self._intervalo = intervalo
        self._tentativas = tentativas
        self._trava = asyncio.Lock()
        self._ultima = 0.0

    async def __aenter__(self) -> ClienteHttp:
        return self

    async def __aexit__(self, *exc) -> None:
        await self._cliente.aclose()

    async def _aguardar_vez(self) -> None:
        loop = asyncio.get_running_loop()
        async with self._trava:
            espera = self._ultima + self._intervalo - loop.time()
            if espera > 0:
                await asyncio.sleep(espera)
            self._ultima = loop.time()

    async def requisicao(self, metodo: str, url: str, **kwargs) -> httpx.Response:
        url_log = httpx.URL(url, params=kwargs.get("params"))
        for tentativa in range(1, self._tentativas + 1):
            async with self._semaforo:
                await self._aguardar_vez()
                try:
                    resp = await self._cliente.request(metodo, url, **kwargs)
                except httpx.TransportError as e:
                    motivo = f"{type(e).__name__}: {e}"
                    espera = None
                else:
                    if resp.status_code not in STATUS_TEMPORARIOS:
                        resp.raise_for_status()
                        return resp
                    motivo = f"HTTP {resp.status_code}"
                    espera = _retry_after(resp)

            if tentativa == self._tentativas:
                raise RuntimeError(f"{metodo} {url_log} falhou após {tentativa} tentativas ({motivo})")
            espera = espera or (2**tentativa + random.random())
            log.warning("%s %s: %s; nova tentativa em %.1fs", metodo, url_log, motivo, espera)
            await asyncio.sleep(espera)
        raise AssertionError("inalcançável")

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.requisicao("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.requisicao("POST", url, **kwargs)


def _retry_after(resp: httpx.Response) -> float | None:
    valor = resp.headers.get("Retry-After")
    if valor and valor.isdigit():
        return min(float(valor), 120.0)
    return None
