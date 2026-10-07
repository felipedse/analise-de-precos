-- Schema do banco de preços. Idempotente: pode ser executado várias vezes.

CREATE TABLE IF NOT EXISTS rede (
    id          serial PRIMARY KEY,
    slug        text NOT NULL UNIQUE,
    nome        text NOT NULL,
    plataforma  text NOT NULL,          -- vtex, osuper, ...
    site        text NOT NULL
);

-- Uma loja física (Osuper tem preço por loja) ou a "loja online" da rede (VTEX).
CREATE TABLE IF NOT EXISTS loja (
    id              serial PRIMARY KEY,
    rede_id         integer NOT NULL REFERENCES rede (id),
    codigo_externo  text NOT NULL,      -- id da loja no site
    nome            text NOT NULL,
    cidade          text,
    uf              char(2),
    UNIQUE (rede_id, codigo_externo)
);

-- Produto como cadastrado em cada rede. O mesmo item físico em redes diferentes
-- vira linhas diferentes; o EAN (quando o site informa) permite cruzá-las.
CREATE TABLE IF NOT EXISTS produto (
    id             bigserial PRIMARY KEY,
    rede_id        integer NOT NULL REFERENCES rede (id),
    sku            text NOT NULL,       -- id do produto/SKU no site
    nome           text NOT NULL,
    marca          text,
    ean            text,
    categoria      text,                -- caminho, ex.: "Mercearia > Arroz e Feijão"
    unidade        text,                -- unidade de venda: un, kg, ...
    fator_unidade  numeric(12, 4),      -- multiplicador da unidade (VTEX unitMultiplier)
    url            text,
    imagem_url     text,
    criado_em      timestamptz NOT NULL DEFAULT now(),
    atualizado_em  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (rede_id, sku)
);
CREATE INDEX IF NOT EXISTS produto_ean_idx ON produto (ean) WHERE ean IS NOT NULL;

-- Uma execução do coletor para uma rede.
CREATE TABLE IF NOT EXISTS coleta (
    id             bigserial PRIMARY KEY,
    rede_id        integer NOT NULL REFERENCES rede (id),
    iniciada_em    timestamptz NOT NULL DEFAULT now(),
    finalizada_em  timestamptz,
    status         text NOT NULL DEFAULT 'executando',  -- executando, ok, erro
    total_precos   integer NOT NULL DEFAULT 0,
    erros          integer NOT NULL DEFAULT 0,
    mensagem       text
);

-- Série histórica: uma linha por produto, loja e coleta.
CREATE TABLE IF NOT EXISTS preco (
    id             bigserial PRIMARY KEY,
    produto_id     bigint NOT NULL REFERENCES produto (id),
    loja_id        integer NOT NULL REFERENCES loja (id),
    coleta_id      bigint NOT NULL REFERENCES coleta (id),
    coletado_em    timestamptz NOT NULL DEFAULT now(),
    preco          numeric(12, 2) NOT NULL,  -- preço efetivo (já com promoção)
    preco_regular  numeric(12, 2),           -- preço "de" / sem desconto
    em_promocao    boolean NOT NULL DEFAULT false,
    disponivel     boolean NOT NULL DEFAULT true,
    estoque        numeric(12, 3)
);
CREATE INDEX IF NOT EXISTS preco_produto_loja_idx ON preco (produto_id, loja_id, coletado_em DESC);
CREATE INDEX IF NOT EXISTS preco_coleta_idx ON preco (coleta_id);

-- Último preço conhecido de cada produto em cada loja.
CREATE OR REPLACE VIEW preco_atual AS
SELECT DISTINCT ON (p.produto_id, p.loja_id)
    r.slug        AS rede,
    l.nome        AS loja,
    l.cidade,
    pr.id         AS produto_id,
    pr.sku,
    pr.ean,
    pr.nome,
    pr.marca,
    pr.categoria,
    p.preco,
    p.preco_regular,
    p.em_promocao,
    p.disponivel,
    p.coletado_em,
    p.loja_id
FROM preco p
JOIN produto pr ON pr.id = p.produto_id
JOIN loja l ON l.id = p.loja_id
JOIN rede r ON r.id = pr.rede_id
ORDER BY p.produto_id, p.loja_id, p.coletado_em DESC;

-- ---------------------------------------------------------------------------
-- Base analítica usada pela API
-- ---------------------------------------------------------------------------

CREATE EXTENSION IF NOT EXISTS unaccent;

-- Minúsculas, sem acento e com espaços colapsados: usado para casar categorias
-- entre redes e para a busca por texto.
CREATE OR REPLACE FUNCTION normalizar_texto(texto text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT regexp_replace(lower(public.unaccent('public.unaccent'::regdictionary, btrim(texto))), '\s+', ' ', 'g')
$$;

-- Segmentos do caminho da categoria ("Mercearia > Arroz e Feijão"), sem normalizar.
CREATE OR REPLACE FUNCTION segmentos_categoria(categoria text) RETURNS text[]
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN nullif(btrim(categoria), '') IS NULL THEN ARRAY['Sem categoria']
        ELSE ARRAY(
            SELECT regexp_replace(btrim(s), '\s+', ' ', 'g')
            FROM unnest(string_to_array(categoria, '>')) WITH ORDINALITY AS t (s, i)
            WHERE btrim(s) <> ''
            ORDER BY i
        )
    END
$$;

-- Caminho normalizado da categoria, ex.: {mercearia, arroz e feijao}.
CREATE OR REPLACE FUNCTION normalizar_categoria(categoria text) RETURNS text[]
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT ARRAY(SELECT normalizar_texto(s) FROM unnest(segmentos_categoria(categoria)) WITH ORDINALITY AS t (s, i) ORDER BY i)
$$;

-- Último preço de cada produto em cada loja, já com os campos derivados que a API
-- filtra e agrega. Materializada para não percorrer o histórico a cada consulta;
-- é atualizada ao fim de cada coleta (banco.atualizar_analise).
CREATE MATERIALIZED VIEW IF NOT EXISTS preco_analise AS
SELECT DISTINCT ON (p.produto_id, p.loja_id)
    p.produto_id,
    p.loja_id,
    pr.rede_id,
    r.slug                                           AS rede,
    r.nome                                           AS rede_nome,
    l.nome                                           AS loja,
    pr.sku,
    pr.ean,
    pr.nome,
    pr.marca,
    pr.categoria,
    normalizar_categoria(pr.categoria)               AS caminho,
    segmentos_categoria(pr.categoria)                AS rotulos,
    normalizar_texto(concat_ws(' ', pr.nome, pr.marca)) AS busca,
    p.preco,
    p.preco_regular,
    p.em_promocao,
    CASE WHEN p.em_promocao AND p.preco_regular > 0
        THEN round((p.preco_regular - p.preco) / p.preco_regular, 4)
    END                                              AS desconto,
    p.disponivel,
    p.coletado_em,
    pr.url,
    pr.imagem_url
FROM preco p
JOIN produto pr ON pr.id = p.produto_id
JOIN loja l ON l.id = p.loja_id
JOIN rede r ON r.id = pr.rede_id
ORDER BY p.produto_id, p.loja_id, p.coletado_em DESC;

CREATE UNIQUE INDEX IF NOT EXISTS preco_analise_pk ON preco_analise (produto_id, loja_id);
CREATE INDEX IF NOT EXISTS preco_analise_loja_idx ON preco_analise (loja_id);
CREATE INDEX IF NOT EXISTS preco_analise_caminho_idx ON preco_analise USING gin (caminho);
