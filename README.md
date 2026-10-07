# Preços SC

Coletor de preços de supermercados de Santa Catarina. Lê os catálogos públicos dos sites, grava
uma série histórica de preços em um PostgreSQL local e oferece uma interface para analisar os preços
por loja e por categoria.

```
backend/    coletor (CLI `precos`) + API FastAPI + amostra de dados versionada
frontend/   interface React (Vite + TypeScript)
```

## Redes suportadas

| Rede            | Plataforma | Granularidade do preço       | EAN | Categoria |
|-----------------|------------|------------------------------|-----|-----------|
| Angeloni        | VTEX       | loja online (preço único)    | sim | sim       |
| Giassi          | VTEX       | loja online (preço único)    | sim | sim       |
| Bistek          | VTEX       | loja online (preço único)    | sim | sim       |
| Koch            | Osuper     | por loja física (13 em SC)   | não | não       |
| Fort Atacadista | Osuper     | por loja física (10 em SC)   | não | não       |

Como cada plataforma é lida:

- **VTEX**: usa a API pública de catálogo (`/api/catalog_system/pub/...`) e percorre a árvore de
  categorias. A API pagina só até o item 2500 de cada consulta, então categorias maiores são divididas
  nas subcategorias. A busca textual (`ft=`) não é usada, porque o robots.txt do Angeloni a proíbe.
- **Osuper**: a busca da plataforma fica atrás de proteção anti-bot, e o coletor **não** tenta
  contorná-la. Ele pega os ids de produto no sitemap público e consulta preço e estoque de cada loja
  na API GraphQL da própria loja, 50 produtos por requisição. As lojas são descobertas pela API e
  filtradas por UF = SC (o Fort também tem lojas em RS e SP).

Para adicionar outra rede que use uma dessas plataformas, basta incluí-la em
[`src/precos/redes.py`](src/precos/redes.py). Uma plataforma nova precisa de um coletor em
`src/precos/coletores/`.

## Como rodar

Pré-requisitos: [uv](https://docs.astral.sh/uv/), Node 20+ e Docker (ou qualquer PostgreSQL 13+).

```bash
docker compose up -d                 # PostgreSQL 16 em localhost:5432 (usuário/senha/banco: precos)

cd backend
cp .env.example .env
uv sync
uv run precos amostra carregar       # carrega a amostra versionada (Giassi + Angeloni)
# ou, para coletar dados novos:
uv run precos init-db                # cria tabelas e views (idempotente)
uv run precos coletar                # coleta todas as redes em paralelo

uv run precos api --recarregar       # API em http://127.0.0.1:8000 (docs em /docs)

cd ../frontend
npm install
npm run dev                          # interface em http://localhost:5173
```

Outros usos (em `backend/`):

```bash
uv run precos redes                         # lista as redes
uv run precos coletar giassi koch           # só algumas redes
uv run precos coletar --limite 100 --dry-run   # teste rápido, sem gravar no banco
uv run precos coletar --intervalo 0.5 --concorrencia 2   # mais devagar com os sites
uv run precos atualizar-analise             # recalcula a base analítica (a coleta já faz isso)
uv run pytest                               # testes (os da API usam o banco precos_teste)
```

Para usar outro banco, defina `DATABASE_URL` no `.env` (e `DATABASE_URL_TESTE` para os testes).
Com `npm run build`, o FastAPI também serve a interface em `http://127.0.0.1:8000/`.

### Agendamento

Cada execução grava um novo ponto da série histórica. Para coletar todo dia às 6h, via cron:

```cron
0 6 * * * cd "/caminho/para/analise de precos/backend" && uv run precos coletar >> coleta.log 2>&1
```

## Interface

- **Lojas**: tabela em árvore loja → categorias (todos os níveis) → produtos. Cada linha mostra
  quantidade de produtos, itens e % em promoção, mínimo, média − 1σ, mediana, média, média + 1σ,
  máximo, desvio padrão, desconto médio e uma barra de dispersão (mín.–máx., faixa ±1σ e mediana,
  em escala log). Cabeçalhos ordenam; a linha de totais é calculada sobre todo o conjunto filtrado.
- **Categorias**: menu lateral com a árvore de categorias. Para o nó escolhido mostra as estatísticas
  por loja e "Todas as lojas", o histograma de preços por loja e as subcategorias lado a lado por loja.
  Clicar numa categoria abre os produtos dela (incluindo subcategorias), com ordenação, paginação e totais.
- **Filtros** (valem para as duas abas e ficam na URL): texto (nome, marca ou EAN), redes, lojas,
  marcas, faixa de preço, só promoção e incluir indisponíveis.

As categorias das redes são casadas pelo texto normalizado (sem acento, minúsculas): "Mercearia >
Açúcar" no Giassi e no Angeloni viram o mesmo nó, mas nomes diferentes ficam separados.

## Modelo de dados

```
rede ─┬─< loja ──────────┐
      ├─< produto ───────┼─< preco >── coleta
      └─< coleta ────────┘
```

- `rede`: a rede de supermercados.
- `loja`: uma loja física (Osuper) ou a "loja online" da rede (VTEX).
- `produto`: produto como cadastrado na rede (`UNIQUE (rede_id, sku)`). O `ean` permite cruzar o
  mesmo item entre redes VTEX.
- `coleta`: uma execução por rede, com status, total de preços e número de erros.
- `preco`: a série histórica, com uma linha por produto, loja e coleta. Guarda o preço efetivo
  (`preco`, já com promoção), o preço "de" (`preco_regular`), `em_promocao`, `disponivel` e `estoque`.
- `preco_atual` (view): o último preço de cada produto em cada loja.
- `preco_analise` (view materializada): o mesmo, com o caminho de categoria normalizado e campos
  derivados (desconto, texto de busca). É a base da API e é recalculada ao fim de cada coleta.

Consultas de exemplo:

```sql
-- Mesmo produto (EAN) em redes diferentes, do mais barato para o mais caro
SELECT rede, nome, preco, em_promocao
FROM preco_atual
WHERE ean = '7896038306053'
ORDER BY preco;

-- Histórico de um produto em uma loja
SELECT coletado_em, preco, preco_regular
FROM preco
WHERE produto_id = 123 AND loja_id = 4
ORDER BY coletado_em;

-- Resultado das últimas coletas
SELECT r.slug, c.iniciada_em, c.status, c.total_precos, c.erros
FROM coleta c JOIN rede r ON r.id = c.rede_id
ORDER BY c.id DESC
LIMIT 10;
```

## Limitações conhecidas

- **VTEX sem regionalização**: o preço vem do canal de venda padrão do site. Se a rede mudar o preço
  conforme o CEP ou a loja escolhida, só o preço padrão é capturado.
- **Osuper sem EAN e sem categoria**: a API GraphQL não expõe esses campos. Para cruzar com outras
  redes vai ser preciso comparar pelo nome (fase de análise).
- **Osuper depende do sitemap**: produtos que não estão no sitemap não são coletados.
- **Itens indisponíveis não são gravados**: no VTEX, cerca de metade do catálogo aparece com preço 0
  e `IsAvailable=false` (produto fora de linha ou sem estoque). Por isso o total gravado é menor que o
  total informado pela API.
- **Estoque**: o VTEX devolve 99999 para "estoque ilimitado"; nesses casos o campo fica `NULL`.
- Os sites podem mudar a estrutura a qualquer momento. Acompanhe `coleta.status` e `coleta.erros`.
- **Dispersão por embalagem**: as estatísticas usam o preço de venda, sem converter para preço por
  kg/L (os sites não informam o tamanho de forma estruturada). Categorias com tamanhos variados têm
  desvio alto, e média − 1σ pode ficar negativa quando a distribuição é muito assimétrica.
- **Categorias entre redes**: o casamento é só pelo nome normalizado; não há taxonomia unificada.
  Koch e Fort aparecem em "Sem categoria".
- `preco_analise` é criada com `IF NOT EXISTS`: se a definição dela mudar, é preciso
  `DROP MATERIALIZED VIEW preco_analise` antes do `init-db`.

## Estrutura

```
backend/
  src/precos/
    cli.py            # comandos: init-db, redes, coletar, atualizar-analise, amostra, api
    coleta.py         # orquestra uma coleta (coletor -> gravador)
    banco.py          # conexão, schema e gravação (upsert de produtos + COPY de preços)
    schema.sql        # tabelas, views e a base analítica preco_analise
    amostra.py        # exporta/carrega a amostra versionada
    redes.py          # redes cadastradas
    http.py           # cliente HTTP com limite de taxa e novas tentativas
    modelos.py        # Rede, Loja, Oferta
    coletores/        # vtex.py (Angeloni, Giassi, Bistek), osuper.py (Koch, Fort)
    api/              # FastAPI: app.py, rotas.py, filtros.py, estatisticas.py
  amostra/            # CSVs .gz da amostra (Giassi + Angeloni)
  tests/              # parsers, banco, amostra e API
frontend/
  src/
    App.tsx           # layout, abas e rotas
    filtros/          # barra de filtros (estado na URL)
    componentes/      # tabelas, barra de dispersão, ordenação
    paginas/          # Lojas.tsx, Categorias.tsx e categorias/ (menu, dispersão, histograma)
```
