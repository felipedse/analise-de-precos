import { useState } from 'react'

export type Direcao = 'asc' | 'desc'

export interface Ordenacao {
  chave: string | null
  direcao: Direcao
}

/** Ciclo do clique no cabeçalho: crescente → decrescente → sem ordenação. */
export function proximaOrdenacao(atual: Ordenacao, chave: string, inicial: Direcao = 'asc'): Ordenacao {
  if (atual.chave !== chave) return { chave, direcao: inicial }
  if (atual.direcao === inicial) return { chave, direcao: inicial === 'asc' ? 'desc' : 'asc' }
  return { chave: null, direcao: 'asc' }
}

export function useOrdenacao(inicial: Ordenacao = { chave: null, direcao: 'asc' }) {
  const [ordenacao, setOrdenacao] = useState<Ordenacao>(inicial)
  const alternar = (chave: string, direcaoInicial: Direcao = 'asc') =>
    setOrdenacao((atual) => proximaOrdenacao(atual, chave, direcaoInicial))
  return { ordenacao, alternar }
}

/** Ordena uma cópia; nulos sempre no fim. Sem chave, mantém a ordem original. */
export function ordenar<T>(
  itens: T[],
  ordenacao: Ordenacao,
  valor: (item: T, chave: string) => number | string | null | undefined,
): T[] {
  const { chave, direcao } = ordenacao
  if (!chave) return itens
  const sinal = direcao === 'asc' ? 1 : -1
  return [...itens].sort((a, b) => {
    const va = valor(a, chave)
    const vb = valor(b, chave)
    if (va === null || va === undefined) return vb === null || vb === undefined ? 0 : 1
    if (vb === null || vb === undefined) return -1
    if (typeof va === 'string' || typeof vb === 'string') return sinal * String(va).localeCompare(String(vb), 'pt-BR')
    return sinal * (va - vb)
  })
}
