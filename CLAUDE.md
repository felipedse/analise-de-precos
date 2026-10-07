# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão geral

`precos-sc`: coletor assíncrono de preços de supermercados de Santa Catarina que grava uma série histórica em PostgreSQL. Todo o código, identificadores, logs e mensagens estão em português — mantenha essa convenção.

## Comandos

Projeto gerenciado com `uv` (Python ≥ 3.10). O `.env` (ver `.env.example`) é carregado pela CLI; `DATABASE_URL` tem como padrão o banco do `docker-compose.yml`.

```bash
docker compose up -d                 # PostgreSQL 16 local (precos/precos@localhost:5432/precos)
uv sync                              # instala dependências (inclui grupo dev)
uv run precos init-db                # aplica src/precos/schema.sql (idempotente)
uv run precos redes                  # lista as redes configuradas
uv run precos coletar                # coleta todas as redes em paralelo
uv run precos coletar koch --limite 100 --dry-run -v   # teste rápido sem gravar no banco
uv run pytest                        # testes (tests/, com src/ no pythonpath)
uv run pytest tests/test_x.py::test_y   # um teste específico
```

Opções de `coletar`: `--limite N` (produtos por rede), `--dry-run`, `--concorrencia`, `--intervalo` (segundos entre requisições ao mesmo site), `--sequencial`. O código de saída é 1 se alguma rede falhar.

## Arquitetura

Fluxo: `cli.py` → `coleta.coletar_rede()` (uma por rede, via `asyncio.gather`) → `Coletor` da plataforma gera lotes de `Oferta` → `banco.Gravador` grava cada lote.

- **`redes.py`** — registro `REDES` de `Rede(slug, nome, plataforma, site, opcoes)`. Adicionar uma rede de plataforma já suportada é só uma entrada aqui; `plataforma` escolhe o coletor em `coletores/__init__.py::COLETORES`.
- **`coletores/base.py`** — interface `Coletor`: `lojas()` (chamado antes) e `coletar(limite)`, um async generator de `list[Oferta]`. Falhas parciais (página/lote) devem incrementar `self.erros` e seguir, não abortar a coleta; exceções que escapam marcam a coleta como `erro`.
- **`coletores/vtex.py`** (Angeloni, Giassi, Bistek) — API pública de catálogo percorrendo a árvore de categorias (`fq=C:/id/`). Não usar busca textual (`ft=`), proibida em alguns robots.txt. A API só pagina até 2500 itens: categorias maiores são subdivididas pelos filhos; folhas ainda maiores são lidas também em `OrderByPriceDESC`. Preço único por rede → uma loja sintética `"online"`. Deduplica SKUs entre categorias.
- **`coletores/osuper.py`** (Koch, Fort) — a busca do site tem anti-bot, então: lojas via GraphQL `onlineStores` (filtradas por UF e `webOnline`), ids de produtos via `sitemap.xml`, e preço/estoque por loja via GraphQL com 50 aliases por consulta. A API exige os cabeçalhos `versioning` e `sessionid`. Preço é por loja física, então o mesmo produto se repete em cada loja.
- **`http.py`** — `ClienteHttp` compartilhado por rede: semáforo de concorrência, intervalo mínimo global entre requisições, retry com backoff exponencial e respeito a `Retry-After` para status temporários. Toda requisição externa deve passar por ele.
- **`banco.py`** — `Gravador` cria/atualiza `rede`, `loja` e a linha de `coleta` em `iniciar()`; em `gravar()` faz upsert em lote dos produtos (via `unnest`, cada SKU uma vez por coleta, preservando campos antigos com `COALESCE`) e insere preços com `COPY`; commit por lote. `finalizar()` faz rollback do lote pendente e registra status/contagens.
- **`schema.sql`** — `rede`, `loja`, `produto` (único por `rede_id, sku`; EAN cruza redes), `coleta`, `preco` (append-only, uma linha por produto×loja×coleta) e a view `preco_atual` (último preço por produto e loja). Mudanças de schema precisam continuar idempotentes (`IF NOT EXISTS` / `OR REPLACE`), pois não há migrações.

Convenção de preço em `Oferta`: `preco` é o preço efetivo (já com promoção), `preco_regular` o preço "de"; `em_promocao` só é verdadeiro quando o promocional é menor que o regular. Valores monetários usam `Decimal` (`modelos.decimal_ou_none`).
