import { Link, useSearchParams } from 'react-router-dom'
import { useApi } from '../api'
import { CabecalhosEstatisticas, CelulasEstatisticas } from '../componentes/colunasEstatisticas'
import { Cabecalho } from '../componentes/Cabecalho'
import { escalaDe } from '../componentes/escala'
import { TabelaProdutos } from '../componentes/TabelaProdutos'
import { useFiltros } from '../filtros/useFiltros'
import type { EstatisticasLoja, RespostaDispersao } from '../tipos'
import { Histograma } from './categorias/Histograma'
import { MenuArvore } from './categorias/MenuArvore'
import { useCaminho, useLinkCategoria, type Visao } from './categorias/rotas'
import { TabelaDispersao } from './categorias/TabelaDispersao'

/** Aba Categorias: menu em árvore à esquerda; dispersão (ou produtos) do nó selecionado à direita. */
export function PaginaCategorias() {
  const caminho = useCaminho()
  const [busca] = useSearchParams()
  const visao: Visao = busca.get('visao') === 'produtos' ? 'produtos' : 'dispersao'
  const { params } = useFiltros()
  const { data, error } = useApi<RespostaDispersao>('/categorias/dispersao', { ...params, caminho })
  const link = useLinkCategoria()

  const rotulos = data?.rotulos ?? caminho
  const titulo = caminho.length ? rotulos[rotulos.length - 1] : 'Todas as categorias'

  return (
    <div className="grid grid-cols-[18rem_minmax(0,1fr)] gap-6">
      <aside className="sticky top-4 max-h-[calc(100vh-8rem)] overflow-y-auto">
        <MenuArvore selecionado={caminho} />
      </aside>
      <section className="min-w-0 space-y-5">
        <header className="space-y-2">
          <nav className="text-sm text-stone-600">
            <Link to={link([])} className="hover:underline">
              Categorias
            </Link>
            {caminho.map((_, i) => (
              <span key={i}>
                {' › '}
                <Link to={link(caminho.slice(0, i + 1))} className="hover:underline">
                  {rotulos[i] ?? caminho[i]}
                </Link>
              </span>
            ))}
          </nav>
          <div className="flex items-center justify-between gap-4">
            <h1 className="text-2xl font-semibold">{titulo}</h1>
            <div className="flex rounded-md border border-stone-300 text-sm">
              {(['dispersao', 'produtos'] as Visao[]).map((v) => (
                <Link
                  key={v}
                  to={link(caminho, v)}
                  className={`px-3 py-1.5 ${visao === v ? 'bg-stone-800 text-white' : 'bg-white hover:bg-stone-100'}`}
                >
                  {v === 'dispersao' ? 'Dispersão' : 'Produtos'}
                </Link>
              ))}
            </div>
          </div>
        </header>

        {error && <p className="text-red-700">Erro: {String(error)}</p>}
        {data && <ResumoPorLoja lojas={data.lojas} />}

        {visao === 'dispersao' ? (
          <>
            <div className="rounded-md border border-stone-300 bg-white p-4">
              <h2 className="mb-2 font-semibold">Distribuição dos preços</h2>
              <Histograma caminho={caminho} />
            </div>
            {data && data.subcategorias.length > 0 && (
              <div>
                <h2 className="mb-2 font-semibold">
                  Subcategorias <span className="text-sm font-normal text-stone-500">(clique para ver os produtos)</span>
                </h2>
                <TabelaDispersao subcategorias={data.subcategorias} />
              </div>
            )}
          </>
        ) : (
          <div className="rounded-md border border-stone-300 bg-white">
            <TabelaProdutos params={{ ...params, caminho }} tamanhoPagina={100} />
          </div>
        )}
      </section>
    </div>
  )
}

/** Estatísticas do nó por loja + "Todas as lojas". */
function ResumoPorLoja({ lojas }: { lojas: EstatisticasLoja[] }) {
  if (!lojas.length) return <p className="text-stone-500">Nenhum produto com esses filtros.</p>
  // Com uma loja só, a linha "Todas as lojas" repetiria os mesmos números.
  if (lojas.length === 2) lojas = lojas.filter((l) => l.loja_id !== null)
  const escala = escalaDe(lojas.map((l) => l.estatisticas))
  const semOrdenacao = { ordenacao: { chave: null, direcao: 'asc' as const }, aoOrdenar: () => {} }
  return (
    <div className="overflow-x-auto rounded-md border border-stone-300 bg-white">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <Cabecalho chave="loja" {...semOrdenacao} className="min-w-64 cursor-default">
              Loja
            </Cabecalho>
            <CabecalhosEstatisticas {...semOrdenacao} />
          </tr>
        </thead>
        <tbody>
          {lojas.map((l) => (
            <tr
              key={l.loja_id ?? 'todas'}
              className={`border-b border-stone-200 ${l.loja_id === null ? 'bg-stone-100 font-semibold' : ''}`}
            >
              <td className="px-2 py-1.5">{l.loja}</td>
              <CelulasEstatisticas estatisticas={l.estatisticas} escala={escala} />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
