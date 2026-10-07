import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { Params } from '../api'

export interface Filtros {
  q: string
  rede: string[]
  loja: number[]
  marca: string[]
  preco_min: string
  preco_max: string
  promocao: boolean
  indisponiveis: boolean
}

const VAZIOS: Filtros = {
  q: '',
  rede: [],
  loja: [],
  marca: [],
  preco_min: '',
  preco_max: '',
  promocao: false,
  indisponiveis: false,
}

export const CHAVES_FILTRO = Object.keys(VAZIOS) as (keyof Filtros)[]

export function lerFiltros(busca: URLSearchParams): Filtros {
  return {
    q: busca.get('q') ?? '',
    rede: busca.getAll('rede'),
    loja: busca.getAll('loja').map(Number).filter(Number.isFinite),
    marca: busca.getAll('marca'),
    preco_min: busca.get('preco_min') ?? '',
    preco_max: busca.get('preco_max') ?? '',
    promocao: busca.get('promocao') === 'true',
    indisponiveis: busca.get('indisponiveis') === 'true',
  }
}

export function filtrosParaParams(f: Filtros): Params {
  return { ...f }
}

export function contarFiltrosAtivos(f: Filtros): number {
  return CHAVES_FILTRO.filter((chave) => {
    const valor = f[chave]
    return Array.isArray(valor) ? valor.length > 0 : Boolean(valor)
  }).length
}

/** Filtros guardados na query string da URL: valem para as duas abas e podem ser compartilhados. */
export function useFiltros() {
  const [busca, setBusca] = useSearchParams()
  const filtros = useMemo(() => lerFiltros(busca), [busca])
  const params = useMemo(() => filtrosParaParams(filtros), [filtros])

  const alterar = useCallback(
    (parcial: Partial<Filtros>) =>
      setBusca(
        (anterior) => {
          const nova = new URLSearchParams(anterior)
          for (const [chave, valor] of Object.entries(parcial)) {
            nova.delete(chave)
            if (Array.isArray(valor)) valor.forEach((v) => nova.append(chave, String(v)))
            else if (valor) nova.set(chave, String(valor))
          }
          return nova
        },
        { replace: true },
      ),
    [setBusca],
  )

  const limpar = useCallback(() => alterar(VAZIOS), [alterar])

  return { filtros, params, alterar, limpar }
}
