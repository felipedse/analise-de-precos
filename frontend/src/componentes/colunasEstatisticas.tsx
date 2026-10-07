import type { ReactNode } from 'react'
import type { Estatisticas } from '../tipos'
import { BarraFaixa } from './BarraFaixa'
import { Cabecalho } from './Cabecalho'
import type { Escala } from './escala'
import { COLUNAS_ESTATISTICAS } from './estatisticas'
import type { Direcao, Ordenacao } from './ordenacao'

export function CabecalhosEstatisticas({
  ordenacao,
  aoOrdenar,
}: {
  ordenacao: Ordenacao
  aoOrdenar: (chave: string, inicial: Direcao) => void
}) {
  return (
    <>
      {COLUNAS_ESTATISTICAS.map((c) => (
        <Cabecalho key={c.chave} chave={c.chave} ordenacao={ordenacao} aoOrdenar={aoOrdenar} dica={c.dica} numerico>
          {c.titulo}
        </Cabecalho>
      ))}
      <th
        className="sticky top-0 z-10 whitespace-nowrap border-b border-stone-300 bg-stone-100 px-2 py-2 text-left font-medium text-stone-700"
        title="Mínimo–máximo (traço), média ± 1σ (faixa) e mediana (marca), em escala logarítmica"
      >
        Dispersão
      </th>
    </>
  )
}

export function CelulasEstatisticas({
  estatisticas,
  escala,
  extra,
}: {
  estatisticas: Estatisticas
  escala: Escala | null
  extra?: ReactNode
}) {
  return (
    <>
      {COLUNAS_ESTATISTICAS.map((c) => (
        <td key={c.chave} className="whitespace-nowrap px-2 py-1.5 text-right tabular-nums">
          {c.formatar(estatisticas[c.chave])}
        </td>
      ))}
      <td className="px-2 py-1">
        <BarraFaixa estatisticas={estatisticas} escala={escala} />
        {extra}
      </td>
    </>
  )
}
