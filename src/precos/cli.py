from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from dotenv import load_dotenv

from precos import banco
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

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if args.comando == "init-db":
        return asyncio.run(_init_db())
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

    print("\nResumo da coleta")
    for r in resultados:
        situacao = f"FALHOU: {r.falha}" if r.falha else "ok"
        print(f"  {r.rede:10} {r.precos:7d} preços  {r.erros:3d} erros  {r.segundos:6.0f}s  {situacao}")
    return 1 if any(r.falha for r in resultados) else 0


if __name__ == "__main__":
    sys.exit(main())
