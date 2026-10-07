import { useState } from 'react'
import { type Params, useApi } from '../api'
import { decimal, inteiro, moeda, pct } from '../formato'
import type { RespostaProdutos } from '../tipos'
import { Cabecalho } from './Cabecalho'
import { type Direcao, type Ordenacao, proximaOrdenacao } from './ordenacao'
import { ResumoEstatisticas } from './ResumoEstatisticas'

interface Props {
  params: Params
  tamanhoPagina?: number
  mostrarLoja?: boolean
  mostrarCategoria?: boolean
}

/** Produtos com ordenação, paginação e totais calculados no servidor. */
export function TabelaProdutos({ params, tamanhoPagina = 50, mostrarLoja = true, mostrarCategoria = true }: Props) {
  const [ordenacao, setOrdenacao] = useState<Ordenacao>({ chave: 'preco', direcao: 'asc' })
  // A página volta para 1 quando filtros ou ordenação mudam.
  const consulta = JSON.stringify([params, ordenacao])
  const [estadoPagina, setEstadoPagina] = useState({ consulta, pagina: 1 })
  const pagina = estadoPagina.consulta === consulta ? estadoPagina.pagina : 1
  const setPagina = (nova: number) => setEstadoPagina({ consulta, pagina: nova })

  const { data, isFetching, error } = useApi<RespostaProdutos>('/produtos', {
    ...params,
    ordenar: ordenacao.chave ?? 'nome',
    direcao: ordenacao.direcao,
    pagina,
    tamanho: tamanhoPagina,
  })
  const aoOrdenar = (chave: string, inicial: Direcao) => setOrdenacao((o) => proximaOrdenacao(o, chave, inicial))
  const paginas = data ? Math.max(1, Math.ceil(data.total_itens / tamanhoPagina)) : 1
  const cab = { ordenacao, aoOrdenar }
  const colunas = 6 + Number(mostrarLoja) + Number(mostrarCategoria)

  if (error) return <p className="p-3 text-sm text-red-700">Erro ao carregar produtos: {String(error)}</p>

  return (
    <div className={`overflow-x-auto ${isFetching ? 'opacity-60' : ''}`}>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <Cabecalho chave="nome" {...cab}>Produto</Cabecalho>
            <Cabecalho chave="marca" {...cab}>Marca</Cabecalho>
            {mostrarLoja && <Cabecalho chave="loja" {...cab}>Loja</Cabecalho>}
            {mostrarCategoria && <Cabecalho chave="categoria" {...cab}>Categoria</Cabecalho>}
            <Cabecalho chave="preco" numerico {...cab} dica="Preço efetivo (já com promoção)">Preço</Cabecalho>
            <Cabecalho chave="preco_regular" numerico {...cab} dica="Preço sem desconto">Preço regular</Cabecalho>
            <Cabecalho chave="desconto" numerico {...cab}>Desconto</Cabecalho>
            <Cabecalho
              chave="z"
              numerico
              {...cab}
              dica="Desvios padrão em relação à média da mesma loja no conjunto filtrado"
            >
              z
            </Cabecalho>
          </tr>
        </thead>
        <tbody>
          {data?.itens.map((p) => (
            <tr key={`${p.produto_id}-${p.loja_id}`} className="border-b border-stone-200 hover:bg-amber-50">
              <td className="max-w-md px-2 py-1.5">
                {p.url ? (
                  <a href={p.url} target="_blank" rel="noreferrer" className="hover:underline">
                    {p.nome}
                  </a>
                ) : (
                  p.nome
                )}
                <div className="text-xs text-stone-500">
                  {p.ean ? `EAN ${p.ean}` : `SKU ${p.sku}`}
                  {!p.disponivel && ' · indisponível'}
                </div>
              </td>
              <td className="px-2 py-1.5">{p.marca ?? '–'}</td>
              {mostrarLoja && <td className="whitespace-nowrap px-2 py-1.5">{p.loja}</td>}
              {mostrarCategoria && <td className="px-2 py-1.5 text-stone-600">{p.rotulos.join(' › ')}</td>}
              <td className="whitespace-nowrap px-2 py-1.5 text-right font-medium tabular-nums">
                {moeda(p.preco)}
                {p.em_promocao && (
                  <span className="ml-1.5 rounded bg-amber-200 px-1 text-xs font-normal text-amber-900">promo</span>
                )}
              </td>
              <td className="whitespace-nowrap px-2 py-1.5 text-right tabular-nums text-stone-600">
                {moeda(p.preco_regular)}
              </td>
              <td className="px-2 py-1.5 text-right tabular-nums">{p.desconto ? pct(p.desconto) : '–'}</td>
              <td className="px-2 py-1.5 text-right tabular-nums">{decimal(p.z)}</td>
            </tr>
          ))}
          {data && data.itens.length === 0 && (
            <tr>
              <td colSpan={colunas} className="px-2 py-4 text-center text-stone-500">
                Nenhum produto com esses filtros.
              </td>
            </tr>
          )}
        </tbody>
        {data && data.total.n > 0 && (
          <tfoot>
            <tr className="border-t-2 border-stone-400 bg-stone-100">
              <td colSpan={colunas} className="px-2 py-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <span className="font-semibold">Totais</span>
                    <ResumoEstatisticas estatisticas={data.total} />
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <button
                      type="button"
                      disabled={pagina <= 1}
                      onClick={() => setPagina(pagina - 1)}
                      className="rounded border border-stone-300 bg-white px-2 py-0.5 disabled:opacity-40"
                    >
                      ‹
                    </button>
                    <span className="tabular-nums">
                      {inteiro((pagina - 1) * tamanhoPagina + 1)}–
                      {inteiro(Math.min(pagina * tamanhoPagina, data.total_itens))} de {inteiro(data.total_itens)}
                    </span>
                    <button
                      type="button"
                      disabled={pagina >= paginas}
                      onClick={() => setPagina(pagina + 1)}
                      className="rounded border border-stone-300 bg-white px-2 py-0.5 disabled:opacity-40"
                    >
                      ›
                    </button>
                  </div>
                </div>
              </td>
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  )
}
