import { useCallback, useEffect, useState } from 'react'
import { useApi } from '../api'
import { Multiselecao } from '../componentes/Multiselecao'
import type { Meta } from '../tipos'
import { contarFiltrosAtivos, useFiltros } from './useFiltros'

/** Filtros globais (texto, redes, lojas, marcas, preço, promoção, disponibilidade). */
export function BarraFiltros() {
  const { filtros, alterar, limpar } = useFiltros()
  const { data: meta } = useApi<Meta>('/meta')
  const [texto, setTexto] = useRascunho(filtros.q, useCallback((q: string) => alterar({ q }), [alterar]))
  const [precoMin, setPrecoMin] = useRascunho(
    filtros.preco_min,
    useCallback((preco_min: string) => alterar({ preco_min }), [alterar]),
  )
  const [precoMax, setPrecoMax] = useRascunho(
    filtros.preco_max,
    useCallback((preco_max: string) => alterar({ preco_max }), [alterar]),
  )

  const ativos = contarFiltrosAtivos(filtros)

  return (
    <div className="flex flex-wrap items-center gap-2">
      <input
        type="search"
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        placeholder="Buscar nome, marca ou EAN"
        className="h-9 w-64 rounded-md border border-stone-300 bg-white px-3 text-sm"
      />
      <Multiselecao
        titulo="Redes"
        opcoes={(meta?.redes ?? []).map((r) => ({ valor: r.slug, rotulo: r.nome }))}
        selecionados={filtros.rede}
        aoMudar={(rede) => alterar({ rede })}
      />
      <Multiselecao
        titulo="Lojas"
        opcoes={(meta?.lojas ?? []).map((l) => ({ valor: String(l.id), rotulo: l.nome, detalhe: l.n }))}
        selecionados={filtros.loja.map(String)}
        aoMudar={(lojas) => alterar({ loja: lojas.map(Number) })}
      />
      <Multiselecao
        titulo="Marcas"
        opcoes={(meta?.marcas ?? []).map((m) => ({ valor: m.marca, rotulo: m.marca, detalhe: m.n }))}
        selecionados={filtros.marca}
        aoMudar={(marca) => alterar({ marca })}
      />
      <div className="flex items-center gap-1 text-sm">
        <span className="text-stone-600">Preço</span>
        <input
          type="number"
          min={0}
          step="0.01"
          value={precoMin}
          onChange={(e) => setPrecoMin(e.target.value)}
          placeholder="mín."
          className="h-9 w-20 rounded-md border border-stone-300 bg-white px-2"
        />
        <span className="text-stone-400">–</span>
        <input
          type="number"
          min={0}
          step="0.01"
          value={precoMax}
          onChange={(e) => setPrecoMax(e.target.value)}
          placeholder="máx."
          className="h-9 w-20 rounded-md border border-stone-300 bg-white px-2"
        />
      </div>
      <label className="flex items-center gap-1.5 text-sm">
        <input type="checkbox" checked={filtros.promocao} onChange={(e) => alterar({ promocao: e.target.checked })} />
        Só em promoção
      </label>
      <label className="flex items-center gap-1.5 text-sm">
        <input
          type="checkbox"
          checked={filtros.indisponiveis}
          onChange={(e) => alterar({ indisponiveis: e.target.checked })}
        />
        Incluir indisponíveis
      </label>
      {ativos > 0 && (
        <button type="button" onClick={limpar} className="h-9 px-2 text-sm text-stone-600 underline">
          Limpar filtros ({ativos})
        </button>
      )}
    </div>
  )
}

/**
 * Campo de texto ligado a um filtro da URL: a digitação só vira filtro depois de uma pausa,
 * e o campo acompanha mudanças externas (ex.: "Limpar filtros").
 */
function useRascunho(externo: string, confirmar: (valor: string) => void) {
  const [rascunho, setRascunho] = useState(externo)
  const [anterior, setAnterior] = useState(externo)
  if (externo !== anterior) {
    setAnterior(externo)
    setRascunho(externo)
  }
  useEffect(() => {
    if (rascunho === externo) return
    const t = setTimeout(() => confirmar(rascunho), 400)
    return () => clearTimeout(t)
  }, [rascunho, externo, confirmar])
  return [rascunho, setRascunho] as const
}
