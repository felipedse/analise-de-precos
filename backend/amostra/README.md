# Amostra de dados

Catálogo completo de duas redes VTEX, coletado em 07/10/2026 com `uv run precos coletar giassi angeloni`:

| Rede     | Loja                   | Preços |
|----------|------------------------|-------:|
| Giassi   | Giassi (loja online)   | 10.394 |
| Angeloni | Angeloni (loja online) | 15.907 |

Um CSV comprimido por tabela (`rede`, `loja`, `produto`, `coleta`, `preco`), com os ids originais.
Só entra a última coleta bem-sucedida de cada rede.

```bash
cd backend
uv run precos amostra carregar                 # banco vazio (aplica o schema antes)
uv run precos amostra carregar --substituir    # apaga os dados existentes antes
uv run precos amostra exportar --rede giassi --rede angeloni   # regera a partir do seu banco
```

Os testes da API (`uv run pytest`) recriam o banco `precos_teste` e carregam esta amostra.
