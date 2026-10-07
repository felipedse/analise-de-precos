import { inteiro, moeda, pct } from '../formato'
import type { Estatisticas } from '../tipos'

export interface Coluna {
  chave: keyof Estatisticas
  titulo: string
  dica: string
  formatar: (v: number | null) => string
}

export const COLUNAS_ESTATISTICAS: Coluna[] = [
  { chave: 'n', titulo: 'Produtos', dica: 'Quantidade de produtos com preço', formatar: inteiro },
  { chave: 'n_promocao', titulo: 'Em promoção', dica: 'Produtos com preço promocional', formatar: inteiro },
  { chave: 'pct_promocao', titulo: '% promoção', dica: 'Parcela dos produtos em promoção', formatar: pct },
  { chave: 'minimo', titulo: 'Mínimo', dica: 'Menor preço', formatar: moeda },
  { chave: 'faixa_inferior', titulo: '−1σ', dica: 'Média menos um desvio padrão', formatar: moeda },
  { chave: 'mediana', titulo: 'Mediana', dica: 'Preço mediano', formatar: moeda },
  { chave: 'media', titulo: 'Média', dica: 'Preço médio', formatar: moeda },
  { chave: 'faixa_superior', titulo: '+1σ', dica: 'Média mais um desvio padrão', formatar: moeda },
  { chave: 'maximo', titulo: 'Máximo', dica: 'Maior preço', formatar: moeda },
  { chave: 'desvio', titulo: 'Desvio (σ)', dica: 'Desvio padrão amostral do preço', formatar: moeda },
  { chave: 'desconto_medio', titulo: 'Desc. médio', dica: 'Desconto médio dos itens em promoção', formatar: pct },
]

export const NUM_COLUNAS_ESTATISTICAS = COLUNAS_ESTATISTICAS.length + 1 // + barra de faixa

/** Valor usado na ordenação por uma coluna de estatística. */
export const valorEstatistica = (e: Estatisticas, chave: string) => e[chave as keyof Estatisticas] as number | null
