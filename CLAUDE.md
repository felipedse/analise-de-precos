# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão geral

`precos-sc`: coletor assíncrono de preços de supermercados de Santa Catarina que grava uma série histórica em PostgreSQL, com uma API FastAPI e uma interface React para analisar os preços. Todo o código, identificadores, logs e mensagens estão em português — mantenha essa convenção.

- `backend/` — pacote Python `precos` (coletor, CLI e API), testes e a amostra de dados (`backend/amostra/`).
- `frontend/` — React + Vite + TypeScript.

## Comandos

Back-end gerenciado com `uv` (Python ≥ 3.10), comandos rodados em `backend/`. O `.env` (ver `backend/.env.example`) é carregado pela CLI e pela API; `DATABASE_URL` tem como padrão o banco do `docker-compose.yml` (na raiz).

```bash
docker compose up -d                 # PostgreSQL 16 local (precos/precos@localhost:5432/precos)
cd backend
uv sync                              # instala dependências (inclui grupo dev)
uv run precos init-db                # aplica src/precos/schema.sql (idempotente)
uv run precos amostra carregar       # carrega a amostra versionada (banco vazio; --substituir apaga antes)
uv run precos redes                  # lista as redes configuradas
uv run precos coletar                # coleta todas as redes em paralelo
uv run precos coletar koch --limite 100 --dry-run -v   # teste rápido sem gravar no banco
uv run precos atualizar-analise      # REFRESH da view materializada preco_analise
uv run precos api --recarregar       # FastAPI em 127.0.0.1:8000
uv run pytest                        # testes (tests/, com src/ no pythonpath)
uv run pytest tests/test_x.py::test_y   # um teste específico
```

Os testes de banco/API (`conftest.py`) recriam o banco de `DATABASE_URL_TESTE` (padrão `precos_teste`) e carregam a amostra; sem PostgreSQL acessível eles são pulados.

Front-end em `frontend/`: `npm install`, `npm run dev` (proxy de `/api` para `127.0.0.1:8000`), `npm test` (vitest), `npm run lint` (oxlint), `npm run build` (tsc + vite; o FastAPI serve `frontend/dist` em `/` se existir).

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

- **`amostra.py`** — `exportar()` grava a última coleta `ok` das redes escolhidas em `backend/amostra/<tabela>.csv.gz` (ids preservados, gzip com `mtime=0` para diffs estáveis); `carregar()` aplica o schema, faz `COPY`, ajusta as sequences e atualiza `preco_analise`.
- **Base analítica** — `schema.sql` define `normalizar_texto`, `segmentos_categoria`, `normalizar_categoria` (caminho `text[]` sem acento/minúsculo, usado para casar categorias entre redes) e a view materializada `preco_analise` (último preço por produto×loja com `caminho`, `rotulos`, `busca`, `desconto`). É atualizada por `banco.atualizar_analise()` ao fim de `coletar`. Como é `CREATE ... IF NOT EXISTS`, mudar a definição exige `DROP` antes.
- **`api/`** — `app.py::criar_app()` (pool `psycopg_pool` com `dict_row`); `rotas.py` com `/api/meta`, `/api/lojas`, `/api/lojas/{id}/nos`, `/api/produtos`, `/api/categorias/{arvore,dispersao,histograma}`; `filtros.py::Filtros.where()` gera o `WHERE` parametrizado comum a tudo (nunca concatenar valores no SQL); `estatisticas.py::AGREGADOS` é o fragmento de min/max/média/mediana/σ reutilizado. Agregações ficam no SQL; o front só ordena irmãos.
- **Front** — filtros na query string (`filtros/useFiltros.ts`); `useApi` (React Query) em `api.ts`; colunas de estatística compartilhadas em `componentes/estatisticas.ts` + `colunasEstatisticas.tsx`; histograma em SVG próprio (`paginas/categorias/Histograma.tsx`, até 3 lojas, cores de `--serie-N` em `index.css`).

Convenção de preço em `Oferta`: `preco` é o preço efetivo (já com promoção), `preco_regular` o preço "de"; `em_promocao` só é verdadeiro quando o promocional é menor que o regular. Valores monetários usam `Decimal` (`modelos.decimal_ou_none`).
