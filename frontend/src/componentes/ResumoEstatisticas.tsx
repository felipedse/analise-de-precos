import { inteiro, moeda, pct } from '../formato'
import type { Estatisticas } from '../tipos'

/** Totais do conjunto filtrado em uma linha compacta. */
export function ResumoEstatisticas({ estatisticas: e }: { estatisticas: Estatisticas }) {
  const itens: [string, string][] = [
    ['Produtos', inteiro(e.n)],
    ['Em promoção', `${inteiro(e.n_promocao)} (${pct(e.pct_promocao)})`],
    ['Mínimo', moeda(e.minimo)],
    ['−1σ', moeda(e.faixa_inferior)],
    ['Mediana', moeda(e.mediana)],
    ['Média', moeda(e.media)],
    ['+1σ', moeda(e.faixa_superior)],
    ['Máximo', moeda(e.maximo)],
    ['Desc. médio', pct(e.desconto_medio)],
  ]
  return (
    <dl className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
      {itens.map(([rotulo, valor]) => (
        <div key={rotulo} className="flex gap-1.5">
          <dt className="text-stone-500">{rotulo}</dt>
          <dd className="font-medium tabular-nums">{valor}</dd>
        </div>
      ))}
    </dl>
  )
}
