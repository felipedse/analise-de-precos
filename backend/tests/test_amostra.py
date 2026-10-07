import asyncio

import psycopg

from precos import amostra


def test_amostra_carregada_por_inteiro(banco):
    for tabela in amostra.COLUNAS:
        (n,) = banco.execute(f"SELECT count(*) FROM {tabela}").fetchone()
        assert n > 0, tabela
    redes = {slug for (slug,) in banco.execute("SELECT slug FROM rede")}
    assert redes == {"giassi", "angeloni"}
    (analise,) = banco.execute("SELECT count(*) FROM preco_analise").fetchone()
    (precos,) = banco.execute("SELECT count(*) FROM preco").fetchone()
    assert analise == precos  # uma coleta por rede: um preço por produto e loja


def test_sequences_continuam_depois_dos_ids_da_amostra(banco):
    (maximo,) = banco.execute("SELECT max(id) FROM produto").fetchone()
    (proximo,) = banco.execute("SELECT nextval(pg_get_serial_sequence('produto', 'id'))").fetchone()
    assert proximo > maximo
    banco.rollback()


def test_exportar_reproduz_a_amostra(url_banco, tmp_path):
    async def exportar():
        async with await psycopg.AsyncConnection.connect(url_banco) as conn:
            return await amostra.exportar(conn, ["giassi", "angeloni"], tmp_path)

    contagens = asyncio.run(exportar())
    for tabela in amostra.COLUNAS:
        assert (tmp_path / f"{tabela}.csv.gz").read_bytes() == (amostra.PASTA_PADRAO / f"{tabela}.csv.gz").read_bytes()
    assert contagens["preco"] > 0


def test_carregar_recusa_banco_com_dados(url_banco):
    async def carregar():
        async with await psycopg.AsyncConnection.connect(url_banco) as conn:
            await amostra.carregar(conn)

    try:
        asyncio.run(carregar())
    except ValueError as e:
        assert "--substituir" in str(e)
    else:
        raise AssertionError("deveria recusar")
