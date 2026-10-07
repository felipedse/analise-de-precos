import { useQuery } from '@tanstack/react-query'

export type Params = Record<string, string | number | boolean | (string | number)[] | null | undefined>

export function paraQuery(params: Params): string {
  const busca = new URLSearchParams()
  for (const [chave, valor] of Object.entries(params)) {
    if (valor === null || valor === undefined || valor === '' || valor === false) continue
    if (Array.isArray(valor)) valor.forEach((v) => busca.append(chave, String(v)))
    else busca.append(chave, String(valor))
  }
  return busca.toString()
}

export async function buscar<T>(rota: string, params: Params = {}): Promise<T> {
  const query = paraQuery(params)
  const resposta = await fetch(`/api${rota}${query ? `?${query}` : ''}`)
  if (!resposta.ok) throw new Error(`${resposta.status} ao buscar ${rota}`)
  return resposta.json() as Promise<T>
}

/** Consulta à API com cache do React Query; a chave inclui rota e parâmetros. */
export function useApi<T>(rota: string, params: Params = {}, ativo = true) {
  return useQuery({
    queryKey: [rota, paraQuery(params)],
    queryFn: () => buscar<T>(rota, params),
    enabled: ativo,
    placeholderData: (anterior) => anterior,
  })
}
