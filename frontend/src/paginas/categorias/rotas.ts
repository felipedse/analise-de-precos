import { useCallback } from 'react'
import { useLocation, useParams } from 'react-router-dom'

export type Visao = 'dispersao' | 'produtos'

/** Caminho normalizado da categoria a partir da URL (/categorias/mercearia/arroz). */
export function useCaminho(): string[] {
  const { '*': resto = '' } = useParams()
  return resto
    .split('/')
    .filter(Boolean)
    .map((s) => decodeURIComponent(s))
}

/** Monta links para outra categoria preservando os filtros da URL. */
export function useLinkCategoria() {
  const { search } = useLocation()
  return useCallback(
    (caminho: string[], visao: Visao = 'dispersao') => {
      const busca = new URLSearchParams(search)
      busca.delete('visao')
      if (visao !== 'dispersao') busca.set('visao', visao)
      const query = busca.toString()
      return `/categorias/${caminho.map(encodeURIComponent).join('/')}${query ? `?${query}` : ''}`
    },
    [search],
  )
}
