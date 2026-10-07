import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../../api'
import { useFiltros } from '../../filtros/useFiltros'
import { inteiro } from '../../formato'
import type { NoArvore } from '../../tipos'
import { useLinkCategoria } from './rotas'

interface Ramo {
  no: NoArvore
  filhos: Ramo[]
}

const chave = (caminho: string[]) => caminho.join('/')

function montarArvore(nos: NoArvore[]): Ramo[] {
  const ramos = new Map<string, Ramo>()
  const raizes: Ramo[] = []
  for (const no of nos) {
    // A API devolve ordenado por caminho: o pai sempre vem antes dos filhos.
    const ramo = { no, filhos: [] }
    ramos.set(chave(no.caminho), ramo)
    const pai = ramos.get(chave(no.caminho.slice(0, -1)))
    if (no.caminho.length > 1 && pai) pai.filhos.push(ramo)
    else raizes.push(ramo)
  }
  return raizes
}

function normalizar(texto: string) {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

/** Menu lateral com a árvore de categorias; o nó selecionado vem da URL. */
export function MenuArvore({ selecionado }: { selecionado: string[] }) {
  const { params } = useFiltros()
  const { data } = useApi<NoArvore[]>('/categorias/arvore', params)
  const link = useLinkCategoria()
  const [abertos, setAbertos] = useState<Set<string>>(new Set())
  const [busca, setBusca] = useState('')

  // Abre os ancestrais do nó selecionado.
  const chaveSelecionado = chave(selecionado)
  const [selecionadoAnterior, setSelecionadoAnterior] = useState<string | null>(null)
  if (chaveSelecionado !== selecionadoAnterior) {
    setSelecionadoAnterior(chaveSelecionado)
    const novos = new Set(abertos)
    selecionado.forEach((_, i) => novos.add(chave(selecionado.slice(0, i + 1))))
    setAbertos(novos)
  }

  const arvore = useMemo(() => montarArvore(data ?? []), [data])

  // Com busca: mostra os nós que casam e seus ancestrais, tudo aberto.
  const visiveis = useMemo(() => {
    const termo = normalizar(busca.trim())
    if (!termo || !data) return null
    const conjunto = new Set<string>()
    for (const no of data) {
      if (normalizar(no.rotulo).includes(termo)) {
        no.caminho.forEach((_, i) => conjunto.add(chave(no.caminho.slice(0, i + 1))))
      }
    }
    return conjunto
  }, [busca, data])

  const alternar = (k: string) =>
    setAbertos((atual) => {
      const novos = new Set(atual)
      if (novos.has(k)) novos.delete(k)
      else novos.add(k)
      return novos
    })

  const renderizar = (ramos: Ramo[], nivel: number) => (
    <ul>
      {ramos
        .filter((r) => !visiveis || visiveis.has(chave(r.no.caminho)))
        .map((r) => {
          const k = chave(r.no.caminho)
          const aberto = visiveis ? true : abertos.has(k)
          const ativo = k === chaveSelecionado
          return (
            <li key={k}>
              <div
                className={`flex items-center gap-1 rounded py-0.5 pr-1 ${ativo ? 'bg-stone-800 text-white' : 'hover:bg-stone-200'}`}
                style={{ paddingLeft: `${nivel * 0.75}rem` }}
              >
                <button
                  type="button"
                  onClick={() => alternar(k)}
                  className={`w-4 shrink-0 text-xs ${r.filhos.length ? '' : 'invisible'}`}
                  aria-label={aberto ? 'Recolher' : 'Expandir'}
                >
                  {aberto ? '▾' : '▸'}
                </button>
                <Link to={link(r.no.caminho)} className="flex-1 truncate" title={r.no.rotulo}>
                  {r.no.rotulo}
                </Link>
                <span className={`text-xs tabular-nums ${ativo ? 'text-stone-300' : 'text-stone-500'}`}>
                  {inteiro(r.no.n)}
                </span>
              </div>
              {aberto && r.filhos.length > 0 && renderizar(r.filhos, nivel + 1)}
            </li>
          )
        })}
    </ul>
  )

  return (
    <nav className="text-sm">
      <input
        type="search"
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
        placeholder="Buscar categoria"
        className="mb-2 h-8 w-full rounded-md border border-stone-300 bg-white px-2"
      />
      <Link
        to={link([])}
        className={`mb-1 block rounded px-1 py-0.5 font-medium ${selecionado.length === 0 ? 'bg-stone-800 text-white' : 'hover:bg-stone-200'}`}
      >
        Todas as categorias
      </Link>
      {data ? renderizar(arvore, 0) : <p className="text-stone-500">Carregando…</p>}
    </nav>
  )
}
