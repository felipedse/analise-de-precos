import { useEffect, useMemo, useRef, useState } from 'react'
import { inteiro } from '../formato'

export interface Opcao {
  valor: string
  rotulo: string
  detalhe?: number
}

interface Props {
  titulo: string
  opcoes: Opcao[]
  selecionados: string[]
  aoMudar: (valores: string[]) => void
  limite?: number
}

/** Botão que abre uma lista com busca e caixas de seleção. */
export function Multiselecao({ titulo, opcoes, selecionados, aoMudar, limite = 200 }: Props) {
  const [aberto, setAberto] = useState(false)
  const [busca, setBusca] = useState('')
  const raiz = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!aberto) return
    const fechar = (e: MouseEvent) => {
      if (!raiz.current?.contains(e.target as Node)) setAberto(false)
    }
    document.addEventListener('mousedown', fechar)
    return () => document.removeEventListener('mousedown', fechar)
  }, [aberto])

  const visiveis = useMemo(() => {
    const termo = normalizar(busca)
    const filtradas = termo ? opcoes.filter((o) => normalizar(o.rotulo).includes(termo)) : opcoes
    // Selecionados sempre aparecem primeiro.
    const marcadas = filtradas.filter((o) => selecionados.includes(o.valor))
    const demais = filtradas.filter((o) => !selecionados.includes(o.valor))
    return [...marcadas, ...demais].slice(0, limite)
  }, [opcoes, busca, selecionados, limite])

  const alternar = (valor: string) =>
    aoMudar(selecionados.includes(valor) ? selecionados.filter((v) => v !== valor) : [...selecionados, valor])

  return (
    <div className="relative" ref={raiz}>
      <button
        type="button"
        onClick={() => setAberto(!aberto)}
        className={`h-9 rounded-md border px-3 text-sm ${
          selecionados.length ? 'border-stone-800 bg-stone-800 text-white' : 'border-stone-300 bg-white hover:bg-stone-100'
        }`}
      >
        {titulo}
        {selecionados.length > 0 && ` (${selecionados.length})`} ▾
      </button>
      {aberto && (
        <div className="absolute z-20 mt-1 w-72 rounded-md border border-stone-300 bg-white p-2 shadow-lg">
          <input
            autoFocus
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar…"
            className="mb-2 h-8 w-full rounded border border-stone-300 px-2 text-sm"
          />
          <ul className="max-h-72 overflow-y-auto text-sm">
            {visiveis.map((o) => (
              <li key={o.valor}>
                <label className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 hover:bg-stone-100">
                  <input type="checkbox" checked={selecionados.includes(o.valor)} onChange={() => alternar(o.valor)} />
                  <span className="flex-1 truncate">{o.rotulo}</span>
                  {o.detalhe !== undefined && <span className="text-xs text-stone-500">{inteiro(o.detalhe)}</span>}
                </label>
              </li>
            ))}
            {visiveis.length === 0 && <li className="px-1 py-1 text-stone-500">Nada encontrado</li>}
          </ul>
          {selecionados.length > 0 && (
            <button type="button" onClick={() => aoMudar([])} className="mt-2 text-xs text-stone-600 underline">
              Limpar seleção
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function normalizar(texto: string) {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}
