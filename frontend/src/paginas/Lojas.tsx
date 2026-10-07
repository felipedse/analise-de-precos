import { useState } from 'react'
import { type Params, useApi } from '../api'
import { CabecalhosEstatisticas, CelulasEstatisticas } from '../componentes/colunasEstatisticas'
import { NUM_COLUNAS_ESTATISTICAS, valorEstatistica } from '../componentes/estatisticas'
import { Cabecalho } from '../componentes/Cabecalho'
import { type Escala, escalaDe } from '../componentes/escala'
import { type Ordenacao, ordenar, useOrdenacao } from '../componentes/ordenacao'
import { TabelaProdutos } from '../componentes/TabelaProdutos'
import { useFiltros } from '../filtros/useFiltros'
import { inteiro } from '../formato'
import type { Estatisticas, RespostaLojas, RespostaNos } from '../tipos'

const TOTAL_COLUNAS = NUM_COLUNAS_ESTATISTICAS + 1

const valorLinha = (rotulo: string, e: Estatisticas, chave: string) =>
  chave === 'rotulo' ? rotulo : valorEstatistica(e, chave)

/** Aba Lojas: tabela em árvore loja → categorias (todos os níveis) → produtos. */
export function PaginaLojas() {
  const { params } = useFiltros()
  const { data, isFetching, error } = useApi<RespostaLojas>('/lojas', params)
  const { ordenacao, alternar } = useOrdenacao()

  if (error) return <p className="text-red-700">Erro ao carregar lojas: {String(error)}</p>
  if (!data) return <p className="text-stone-500">Carregando…</p>

  const linhas = ordenar(data.linhas, ordenacao, (l, chave) => valorLinha(l.loja, l.estatisticas, chave))
  const escala = escalaDe(data.linhas.map((l) => l.estatisticas))

  return (
    <div className={`overflow-x-auto rounded-md border border-stone-300 bg-white ${isFetching ? 'opacity-70' : ''}`}>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <Cabecalho chave="rotulo" ordenacao={ordenacao} aoOrdenar={alternar} className="min-w-72">
              Loja / categoria
            </Cabecalho>
            <CabecalhosEstatisticas ordenacao={ordenacao} aoOrdenar={alternar} />
          </tr>
        </thead>
        <tbody>
          {linhas.map((l) => (
            <NoLoja
              key={l.loja_id}
              lojaId={l.loja_id}
              caminho={[]}
              rotulo={l.loja}
              estatisticas={l.estatisticas}
              temFilhos
              nivel={0}
              escala={escala}
              params={params}
              ordenacao={ordenacao}
            />
          ))}
          {linhas.length === 0 && (
            <tr>
              <td colSpan={TOTAL_COLUNAS} className="px-2 py-4 text-center text-stone-500">
                Nenhuma loja com esses filtros.
              </td>
            </tr>
          )}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-stone-400 bg-stone-100 font-semibold">
            <td className="px-2 py-2">Totais ({linhas.length} lojas)</td>
            <CelulasEstatisticas estatisticas={data.total} escala={escala} />
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

interface PropsNo {
  lojaId: number
  caminho: string[]
  rotulo: string
  estatisticas: Estatisticas
  temFilhos: boolean
  nivel: number
  escala: Escala | null
  params: Params
  ordenacao: Ordenacao
}

/** Uma linha (loja ou categoria) que, aberta, carrega as subcategorias e os produtos do nó. */
function NoLoja({ lojaId, caminho, rotulo, estatisticas, temFilhos, nivel, escala, params, ordenacao }: PropsNo) {
  const [aberto, setAberto] = useState(false)
  return (
    <>
      <tr
        className={`cursor-pointer border-b border-stone-200 hover:bg-amber-50 ${nivel === 0 ? 'font-semibold' : ''}`}
        onClick={() => setAberto(!aberto)}
      >
        <td className="px-2 py-1.5" style={{ paddingLeft: `${0.5 + nivel * 1.25}rem` }}>
          <span className="inline-block w-4 text-stone-500">{aberto ? '▾' : '▸'}</span>
          {rotulo}
          {!temFilhos && <span className="ml-1 text-xs font-normal text-stone-400">(produtos)</span>}
        </td>
        <CelulasEstatisticas estatisticas={estatisticas} escala={escala} />
      </tr>
      {aberto && (
        <FilhosDoNo lojaId={lojaId} caminho={caminho} nivel={nivel + 1} params={params} ordenacao={ordenacao} />
      )}
    </>
  )
}

function FilhosDoNo({
  lojaId,
  caminho,
  nivel,
  params,
  ordenacao,
}: Pick<PropsNo, 'lojaId' | 'caminho' | 'nivel' | 'params' | 'ordenacao'>) {
  const { data, error } = useApi<RespostaNos>(`/lojas/${lojaId}/nos`, { ...params, caminho })
  const [produtosAbertos, setProdutosAbertos] = useState(false)
  const recuo = { paddingLeft: `${0.5 + nivel * 1.25}rem` }

  if (error || !data)
    return (
      <tr>
        <td colSpan={TOTAL_COLUNAS} className="px-2 py-1.5 text-stone-500" style={recuo}>
          {error ? `Erro: ${String(error)}` : 'Carregando…'}
        </td>
      </tr>
    )

  const filhos = ordenar(data.filhos, ordenacao, (f, chave) => valorLinha(f.rotulo, f.estatisticas, chave))
  const escala = escalaDe(data.filhos.map((f) => f.estatisticas))
  // Folha: mostra os produtos direto, sem um clique a mais.
  const mostrarProdutos = produtosAbertos || filhos.length === 0

  return (
    <>
      {filhos.map((f) => (
        <NoLoja
          key={f.caminho.join('/')}
          lojaId={lojaId}
          caminho={f.caminho}
          rotulo={f.rotulo}
          estatisticas={f.estatisticas}
          temFilhos={f.tem_filhos}
          nivel={nivel}
          escala={escala}
          params={params}
          ordenacao={ordenacao}
        />
      ))}
      {data.produtos_diretos > 0 && filhos.length > 0 && (
        <tr className="cursor-pointer border-b border-stone-200 hover:bg-amber-50" onClick={() => setProdutosAbertos(!produtosAbertos)}>
          <td colSpan={TOTAL_COLUNAS} className="px-2 py-1.5 italic text-stone-600" style={recuo}>
            <span className="inline-block w-4 not-italic text-stone-500">{produtosAbertos ? '▾' : '▸'}</span>
            {inteiro(data.produtos_diretos)} produtos sem subcategoria
          </td>
        </tr>
      )}
      {data.produtos_diretos > 0 && mostrarProdutos && (
        <tr>
          <td colSpan={TOTAL_COLUNAS} className="border-b border-stone-300 bg-stone-50 py-2 pr-2" style={recuo}>
            <div className="rounded border border-stone-200 bg-white">
              <TabelaProdutos
                params={{ ...params, loja: [lojaId], caminho, exato: true }}
                tamanhoPagina={25}
                mostrarLoja={false}
                mostrarCategoria={false}
              />
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
