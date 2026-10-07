import { moeda } from '../formato'
import type { Estatisticas } from '../tipos'
import { type Escala, posicao } from './escala'

const LARGURA = 160
const ALTURA = 18

/**
 * Mini box plot em escala log: traço do mínimo ao máximo, faixa média ± 1σ e marca da mediana.
 * Todas as linhas de uma mesma tabela/grupo usam a mesma escala para serem comparáveis.
 */
export function BarraFaixa({ estatisticas: e, escala }: { estatisticas: Estatisticas; escala: Escala | null }) {
  if (!escala || e.minimo === null || e.maximo === null || e.mediana === null) return null
  const x = (v: number) => posicao(v, escala, LARGURA - 4) + 2
  const inferior = Math.max(e.faixa_inferior ?? e.minimo, e.minimo)
  const superior = Math.min(e.faixa_superior ?? e.maximo, e.maximo)
  const dica =
    `mín. ${moeda(e.minimo)} · −1σ ${moeda(e.faixa_inferior)} · mediana ${moeda(e.mediana)}` +
    ` · +1σ ${moeda(e.faixa_superior)} · máx. ${moeda(e.maximo)} (escala log)`
  return (
    <svg width={LARGURA} height={ALTURA} role="img" aria-label={dica} className="block">
      <title>{dica}</title>
      <line x1={x(e.minimo)} x2={x(e.maximo)} y1={ALTURA / 2} y2={ALTURA / 2} stroke="#a8a29e" strokeWidth={2} />
      <line x1={x(e.minimo)} x2={x(e.minimo)} y1={5} y2={ALTURA - 5} stroke="#a8a29e" strokeWidth={2} />
      <line x1={x(e.maximo)} x2={x(e.maximo)} y1={5} y2={ALTURA - 5} stroke="#a8a29e" strokeWidth={2} />
      {e.desvio !== null && (
        <rect
          x={x(inferior)}
          width={Math.max(x(superior) - x(inferior), 2)}
          y={4}
          height={ALTURA - 8}
          rx={2}
          fill="var(--serie-1)"
          fillOpacity={0.35}
          stroke="var(--serie-1)"
          strokeWidth={1}
        />
      )}
      <line x1={x(e.mediana)} x2={x(e.mediana)} y1={2} y2={ALTURA - 2} stroke="#1c1917" strokeWidth={2} />
    </svg>
  )
}
