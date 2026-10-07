import type { ReactNode } from 'react'
import type { Direcao, Ordenacao } from './ordenacao'

interface Props {
  chave: string
  ordenacao: Ordenacao
  aoOrdenar: (chave: string, inicial: Direcao) => void
  children: ReactNode
  dica?: string
  numerico?: boolean
  className?: string
}

/** Cabeçalho de coluna clicável que mostra a direção da ordenação. */
export function Cabecalho({ chave, ordenacao, aoOrdenar, children, dica, numerico, className = '' }: Props) {
  const ativo = ordenacao.chave === chave
  const seta = ativo ? (ordenacao.direcao === 'asc' ? '▲' : '▼') : ''
  return (
    <th
      title={dica}
      aria-sort={ativo ? (ordenacao.direcao === 'asc' ? 'ascending' : 'descending') : 'none'}
      className={`sticky top-0 z-10 cursor-pointer select-none whitespace-nowrap border-b border-stone-300 bg-stone-100 px-2 py-2 font-medium text-stone-700 hover:bg-stone-200 ${
        numerico ? 'text-right' : 'text-left'
      } ${className}`}
      onClick={() => aoOrdenar(chave, numerico ? 'desc' : 'asc')}
    >
      {children}
      <span className="ml-1 inline-block w-3 text-xs text-stone-500">{seta}</span>
    </th>
  )
}
