export interface Estatisticas {
  n: number
  n_promocao: number
  pct_promocao: number | null
  media: number | null
  mediana: number | null
  minimo: number | null
  maximo: number | null
  desvio: number | null
  faixa_inferior: number | null
  faixa_superior: number | null
  desconto_medio: number | null
}

export interface Meta {
  redes: { slug: string; nome: string; ultima_coleta: string | null }[]
  lojas: { id: number; nome: string; rede: string; rede_nome: string; n: number }[]
  marcas: { marca: string; n: number }[]
}

export interface LinhaLoja {
  loja_id: number
  loja: string
  rede: string
  rede_nome: string
  estatisticas: Estatisticas
}

export interface RespostaLojas {
  linhas: LinhaLoja[]
  total: Estatisticas
}

export interface No {
  caminho: string[]
  rotulo: string
  tem_filhos: boolean
  estatisticas: Estatisticas
}

export interface RespostaNos {
  filhos: No[]
  produtos_diretos: number
}

export interface Produto {
  produto_id: number
  loja_id: number
  loja: string
  rede: string
  rede_nome: string
  sku: string
  ean: string | null
  nome: string
  marca: string | null
  categoria: string | null
  rotulos: string[]
  preco: number
  preco_regular: number | null
  em_promocao: boolean
  desconto: number | null
  disponivel: boolean
  coletado_em: string
  url: string | null
  imagem_url: string | null
  z: number | null
}

export interface RespostaProdutos {
  itens: Produto[]
  total_itens: number
  total: Estatisticas
}

export interface NoArvore {
  caminho: string[]
  rotulo: string
  n: number
  lojas: number
}

export interface EstatisticasLoja {
  loja_id: number | null // null = "Todas as lojas"
  loja: string
  rede: string | null
  estatisticas: Estatisticas
}

export interface Subcategoria {
  caminho: string[]
  rotulo: string
  tem_filhos: boolean
  lojas: EstatisticasLoja[]
}

export interface RespostaDispersao {
  caminho: string[]
  rotulos: string[]
  lojas: EstatisticasLoja[]
  subcategorias: Subcategoria[]
}

export interface Faixa {
  inicio: number
  fim: number
  transbordo: boolean
  contagens: Record<string, number>
}

export interface RespostaHistograma {
  faixas: Faixa[]
  lojas: EstatisticasLoja[]
}
