import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { useApi } from './api'
import { BarraFiltros } from './filtros/BarraFiltros'
import { CHAVES_FILTRO } from './filtros/useFiltros'
import { PaginaCategorias } from './paginas/Categorias'
import { PaginaLojas } from './paginas/Lojas'
import type { Meta } from './tipos'

const cliente = new QueryClient({ defaultOptions: { queries: { staleTime: 5 * 60_000, retry: 1 } } })

export default function App() {
  return (
    <QueryClientProvider client={cliente}>
      <BrowserRouter>
        <Layout />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

/** Links das abas levam só os filtros (não a visão de uma aba para a outra). */
function useBuscaDosFiltros() {
  const { search } = useLocation()
  const atual = new URLSearchParams(search)
  const filtros = new URLSearchParams()
  for (const chave of CHAVES_FILTRO) atual.getAll(chave).forEach((v) => filtros.append(chave, v))
  const texto = filtros.toString()
  return texto ? `?${texto}` : ''
}

function Layout() {
  const busca = useBuscaDosFiltros()
  const { data: meta } = useApi<Meta>('/meta')
  const aba = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-1.5 text-sm font-medium ${isActive ? 'bg-stone-800 text-white' : 'text-stone-700 hover:bg-stone-200'}`

  return (
    <div className="mx-auto max-w-[1600px] px-4 py-4">
      <header className="mb-4 space-y-3">
        <div className="flex flex-wrap items-center gap-4">
          <span className="text-lg font-semibold">Preços SC</span>
          <nav className="flex gap-1">
            <NavLink to={`/lojas${busca}`} className={aba}>
              Lojas
            </NavLink>
            <NavLink to={`/categorias${busca}`} className={aba}>
              Categorias
            </NavLink>
          </nav>
          {meta && (
            <span className="ml-auto text-xs text-stone-500">
              Última coleta:{' '}
              {meta.redes
                .map((r) => `${r.nome} ${r.ultima_coleta ? new Date(r.ultima_coleta).toLocaleDateString('pt-BR') : '–'}`)
                .join(' · ')}
            </span>
          )}
        </div>
        <BarraFiltros />
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/lojas" replace />} />
          <Route path="/lojas" element={<PaginaLojas />} />
          <Route path="/categorias/*" element={<PaginaCategorias />} />
          <Route path="*" element={<p>Página não encontrada.</p>} />
        </Routes>
      </main>
    </div>
  )
}
