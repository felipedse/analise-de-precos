import { useState } from 'react'
import { useApi } from '../../api'
import { useFiltros } from '../../filtros/useFiltros'
import { inteiro, moeda, pct } from '../../formato'
import type { RespostaHistograma } from '../../tipos'

const CORES = ['var(--serie-1)', 'var(--serie-2)', 'var(--serie-3)']
const MAX_SERIES = CORES.length

const LARGURA = 860
const ALTURA = 280
const MARGEM = { topo: 16, direita: 12, base: 44, esquerda: 52 }

type Modo = 'contagem' | 'percentual'

/**
 * Histograma do preço no nó, com uma série por loja (até 3) e linhas de mediana (contínua)
 * e média ± 1σ (tracejadas). Faixas lineares do mínimo ao percentil 99; o resto vai para a última.
 */
export function Histograma({ caminho }: { caminho: string[] }) {
  const { params } = useFiltros()
  const { data } = useApi<RespostaHistograma>('/categorias/histograma', { ...params, caminho, faixas: 30 })
  const [modo, setModo] = useState<Modo>('contagem')
  const [foco, setFoco] = useState<number | null>(null)

  if (!data) return <div className="h-72 text-stone-500">Carregando…</div>
  if (!data.faixas.length) return <p className="text-stone-500">Sem preços para mostrar.</p>

  // Cor fixa por loja (ordem do id), para não trocar quando os filtros mudam a ordem.
  const lojas = [...data.lojas].sort((a, b) => (a.loja_id ?? 0) - (b.loja_id ?? 0)).slice(0, MAX_SERIES)
  const omitidas = data.lojas.length - lojas.length
  const totalLoja = new Map(data.lojas.map((l) => [String(l.loja_id), l.estatisticas.n]))
  const valor = (contagem: number, lojaId: string) =>
    modo === 'contagem' ? contagem : contagem / (totalLoja.get(lojaId) || 1)

  const largura = LARGURA - MARGEM.esquerda - MARGEM.direita
  const altura = ALTURA - MARGEM.topo - MARGEM.base
  const nFaixas = data.faixas.length
  const passo = largura / nFaixas
  const maximoY = Math.max(
    ...data.faixas.flatMap((f) => lojas.map((l) => valor(f.contagens[String(l.loja_id)] ?? 0, String(l.loja_id)))),
    modo === 'contagem' ? 1 : 0.01,
  )
  const y = (v: number) => MARGEM.topo + altura - (v / maximoY) * altura
  const ticksY = [0, 0.25, 0.5, 0.75, 1].map((t) => t * maximoY)

  // Posição x de um preço (só na parte linear; a faixa de transbordo não tem escala).
  const normais = data.faixas.filter((f) => !f.transbordo)
  const inicio = normais[0].inicio
  const fim = normais[normais.length - 1].fim
  const xPreco = (preco: number) =>
    preco < inicio || preco > fim ? null : MARGEM.esquerda + ((preco - inicio) / (fim - inicio)) * normais.length * passo

  const larguraBarra = Math.max((passo - 4) / lojas.length - 1, 1)
  const formatarY = modo === 'contagem' ? inteiro : pct
  const rotuloFaixa = (i: number) => {
    const f = data.faixas[i]
    return f.transbordo ? `≥ ${moeda(f.inicio)}` : `${moeda(f.inicio)} – ${moeda(f.fim)}`
  }
  const cadaRotulo = Math.ceil(nFaixas / 8)
  const temTransbordo = data.faixas[nFaixas - 1].transbordo

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
          {lojas.map((l, i) => (
            <li key={l.loja_id} className="flex items-center gap-1.5">
              <span className="inline-block h-3 w-3 rounded-sm" style={{ background: CORES[i] }} />
              <span className="font-medium">{l.loja}</span>
              <span className="text-stone-600">
                mediana {moeda(l.estatisticas.mediana)} · média ± 1σ {moeda(l.estatisticas.faixa_inferior)} a{' '}
                {moeda(l.estatisticas.faixa_superior)}
              </span>
            </li>
          ))}
        </ul>
        <div className="flex rounded-md border border-stone-300 text-xs">
          {(['contagem', 'percentual'] as Modo[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setModo(m)}
              className={`px-2 py-1 ${modo === m ? 'bg-stone-800 text-white' : 'bg-white hover:bg-stone-100'}`}
            >
              {m === 'contagem' ? 'Produtos' : '% da loja'}
            </button>
          ))}
        </div>
      </div>
      {omitidas > 0 && (
        <p className="mb-1 text-xs text-stone-500">
          Mostrando {MAX_SERIES} lojas; filtre por loja para comparar as outras {omitidas}.
        </p>
      )}
      <div className="relative">
        <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} className="h-auto w-full" role="img" aria-label="Histograma de preços">
          {ticksY.map((t) => (
            <g key={t}>
              <line x1={MARGEM.esquerda} x2={LARGURA - MARGEM.direita} y1={y(t)} y2={y(t)} stroke="#e7e5e4" />
              <text x={MARGEM.esquerda - 6} y={y(t) + 4} textAnchor="end" fontSize={11} fill="#78716c">
                {formatarY(t)}
              </text>
            </g>
          ))}
          {data.faixas.map((f, i) => {
            const x0 = MARGEM.esquerda + i * passo
            return (
              <g key={i} onMouseEnter={() => setFoco(i)} onMouseLeave={() => setFoco(null)}>
                <rect x={x0} y={MARGEM.topo} width={passo} height={altura} fill={foco === i ? '#f5f5f4' : 'transparent'} />
                {lojas.map((l, j) => {
                  const v = valor(f.contagens[String(l.loja_id)] ?? 0, String(l.loja_id))
                  const topo = y(v)
                  return (
                    <rect
                      key={l.loja_id}
                      x={x0 + 2 + j * (larguraBarra + 1)}
                      y={topo}
                      width={larguraBarra}
                      height={Math.max(MARGEM.topo + altura - topo, 0)}
                      rx={1.5}
                      fill={CORES[j]}
                    />
                  )
                })}
                {f.transbordo ? (
                  <text x={x0 + passo} y={ALTURA - MARGEM.base + 16} textAnchor="end" fontSize={11} fill="#78716c">
                    ≥ {moeda(f.inicio)}
                  </text>
                ) : (
                  i % cadaRotulo === 0 &&
                  !(temTransbordo && i > nFaixas - 1 - cadaRotulo) && (
                    <text x={x0} y={ALTURA - MARGEM.base + 16} fontSize={11} fill="#78716c">
                      {moeda(f.inicio)}
                    </text>
                  )
                )}
              </g>
            )
          })}
          {lojas.map((l, j) => {
            const e = l.estatisticas
            const linhas: [number | null, boolean][] = [
              [e.mediana, false],
              [e.faixa_inferior, true],
              [e.faixa_superior, true],
            ]
            return linhas.map(([preco, tracejada], k) => {
              const x = preco === null ? null : xPreco(preco)
              if (x === null) return null
              return (
                <line
                  key={`${l.loja_id}-${k}`}
                  x1={x}
                  x2={x}
                  y1={MARGEM.topo}
                  y2={MARGEM.topo + altura}
                  stroke={CORES[j]}
                  strokeWidth={2}
                  strokeDasharray={tracejada ? '5 4' : undefined}
                  pointerEvents="none"
                />
              )
            })
          })}
          <line
            x1={MARGEM.esquerda}
            x2={LARGURA - MARGEM.direita}
            y1={MARGEM.topo + altura}
            y2={MARGEM.topo + altura}
            stroke="#a8a29e"
          />
          <text x={LARGURA / 2} y={ALTURA - 6} textAnchor="middle" fontSize={11} fill="#57534e">
            Preço (linha contínua: mediana · tracejadas: média ± 1σ)
          </text>
        </svg>
        {foco !== null && (
          <div
            className="pointer-events-none absolute top-2 z-10 rounded-md border border-stone-300 bg-white px-3 py-2 text-xs shadow"
            style={{
              left: `${((MARGEM.esquerda + (foco + 0.5) * passo) / LARGURA) * 100}%`,
              transform: foco > nFaixas / 2 ? 'translateX(-105%)' : 'translateX(5%)',
            }}
          >
            <div className="mb-1 font-medium">{rotuloFaixa(foco)}</div>
            {lojas.map((l, j) => {
              const n = data.faixas[foco].contagens[String(l.loja_id)] ?? 0
              return (
                <div key={l.loja_id} className="flex items-center gap-1.5">
                  <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: CORES[j] }} />
                  {l.loja}: {inteiro(n)} ({pct(n / (totalLoja.get(String(l.loja_id)) || 1))})
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
