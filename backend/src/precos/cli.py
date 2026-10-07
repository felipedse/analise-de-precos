from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from precos import amostra, banco
from precos.coleta import coletar_rede
from precos.redes import REDES


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="precos", description="Coleta de preços de supermercados de SC")
    parser.add_argument("-v", "--verbose", action="store_true", help="log detalhado")
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("init-db", help="cria as tabelas no PostgreSQL")
    sub.add_parser("redes", help="lista as redes suportadas")

    p = sub.add_parser("coletar", help="coleta preços e grava no banco")
    p.add_argument("redes", nargs="*", metavar="REDE", help=f"redes a coletar (padrão: todas). Opções: {', '.join(REDES)}")
    p.add_argument("--limite", type=int, help="máximo de produtos por rede (útil para testes)")
    p.add_argument("--dry-run", action="store_true", help="coleta sem gravar no banco")
    p.add_argument("--concorrencia", type=int, default=4, help="requisições simultâneas por site (padrão: 4)")
    p.add_argument("--intervalo", type=float, default=0.2, help="intervalo mínimo entre requisições a um site, em segundos")
    p.add_argument("--sequencial", action="store_true", help="coleta uma rede por vez em vez de todas em paralelo")

    sub.add_parser("atualizar-analise", help="recalcula a base analítica (preco_analise) usada pela API")

    p = sub.add_parser("amostra", help="exporta ou carrega a amostra de dados versionada")
    sub_amostra = p.add_subparsers(dest="acao", required=True)
    pe = sub_amostra.add_parser("exportar", help="grava a última coleta das redes em CSVs comprimidos")
    pe.add_argument("--rede", action="append", required=True, help="rede a exportar (pode repetir)")
    pe.add_argument("--pasta", type=Path, default=amostra.PASTA_PADRAO, help="pasta de destino")
    pc = sub_amostra.add_parser("carregar", help="carrega a amostra no banco")
    pc.add_argument("--pasta", type=Path, default=amostra.PASTA_PADRAO, help="pasta de origem")
    pc.add_argument("--substituir", action="store_true", help="apaga os dados existentes antes de carregar")

    p = sub.add_parser("api", help="sobe a API HTTP (FastAPI)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--porta", type=int, default=8000)
    p.add_argument("--recarregar", action="store_true", help="reinicia ao alterar o código (desenvolvimento)")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if args.comando == "init-db":
        return asyncio.run(_init_db())
    if args.comando == "atualizar-analise":
        return asyncio.run(_atualizar_analise())
    if args.comando == "amostra":
        return asyncio.run(_amostra(args))
    if args.comando == "api":
        import uvicorn

        uvicorn.run("precos.api.app:criar_app", factory=True, host=args.host, port=args.porta, reload=args.recarregar)
        return 0
    if args.comando == "redes":
        for r in REDES.values():
            print(f"{r.slug:10} {r.nome:18} {r.plataforma:8} {r.site}")
        return 0
    return asyncio.run(_coletar(args))


async def _init_db() -> int:
    conn = await banco.conectar()
    async with conn:
        await banco.criar_schema(conn)
    print("Schema criado/atualizado.")
    return 0


async def _atualizar_analise() -> int:
    conn = await banco.conectar()
    async with conn:
        await banco.atualizar_analise(conn)
    print("Base analítica atualizada.")
    return 0


async def _amostra(args: argparse.Namespace) -> int:
    conn = await banco.conectar()
    async with conn:
        try:
            if args.acao == "exportar":
                contagens = await amostra.exportar(conn, args.rede, args.pasta)
            else:
                contagens = await amostra.carregar(conn, args.pasta, args.substituir)
        except ValueError as e:
            print(f"Erro: {e}", file=sys.stderr)
            return 2
    for tabela, n in contagens.items():
        print(f"  {tabela:8} {n:8d} linhas")
    return 0


async def _coletar(args: argparse.Namespace) -> int:
    desconhecidas = [r for r in args.redes if r not in REDES]
    if desconhecidas:
        print(f"Rede(s) desconhecida(s): {', '.join(desconhecidas)}. Opções: {', '.join(REDES)}", file=sys.stderr)
        return 2
    redes = [REDES[r] for r in args.redes] if args.redes else list(REDES.values())

    def tarefa(rede):
        return coletar_rede(
            rede,
            limite=args.limite,
            gravar=not args.dry_run,
            concorrencia=args.concorrencia,
            intervalo=args.intervalo,
        )

    if args.sequencial:
        resultados = [await tarefa(r) for r in redes]
    else:
        resultados = await asyncio.gather(*(tarefa(r) for r in redes))

    if not args.dry_run and any(r.precos for r in resultados):
        await _atualizar_analise()

    print("\nResumo da coleta")
    for r in resultados:
        situacao = f"FALHOU: {r.falha}" if r.falha else "ok"
        print(f"  {r.rede:10} {r.precos:7d} preços  {r.erros:3d} erros  {r.segundos:6.0f}s  {situacao}")
    return 1 if any(r.falha for r in resultados) else 0


if __name__ == "__main__":
    sys.exit(main())
