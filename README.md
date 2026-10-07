# Preços SC

Coletor de preços de supermercados de Santa Catarina. Lê os catálogos públicos dos sites e grava
uma série histórica de preços em um PostgreSQL local.

Nesta primeira fase, o projeto só faz a **captura**. A API e a apresentação vêm depois.

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

Pré-requisitos: [uv](https://docs.astral.sh/uv/) e Docker (ou qualquer PostgreSQL 13+).

```bash
cp .env.example .env
docker compose up -d          # PostgreSQL 16 em localhost:5432 (usuário/senha/banco: precos)
uv sync
uv run precos init-db         # cria tabelas e views (idempotente)
uv run precos coletar         # coleta todas as redes em paralelo
```

Outros usos:

```bash
uv run precos redes                         # lista as redes
uv run precos coletar giassi koch           # só algumas redes
uv run precos coletar --limite 100 --dry-run   # teste rápido, sem gravar no banco
uv run precos coletar --intervalo 0.5 --concorrencia 2   # mais devagar com os sites
uv run pytest                               # testes
```

Para usar outro banco, defina `DATABASE_URL` no `.env`.

### Agendamento

Cada execução grava um novo ponto da série histórica. Para coletar todo dia às 6h, via cron:

```cron
0 6 * * * cd "/caminho/para/analise de precos" && uv run precos coletar >> coleta.log 2>&1
```

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

## Estrutura

```
src/precos/
  cli.py            # comandos: init-db, redes, coletar
  coleta.py         # orquestra uma coleta (coletor -> gravador)
  banco.py          # conexão, schema e gravação (upsert de produtos + COPY de preços)
  schema.sql        # tabelas e views
  redes.py          # redes cadastradas
  http.py           # cliente HTTP com limite de taxa e novas tentativas
  modelos.py        # Rede, Loja, Oferta
  coletores/
    vtex.py         # Angeloni, Giassi, Bistek
    osuper.py       # Koch, Fort Atacadista
tests/              # testes dos parsers
```
