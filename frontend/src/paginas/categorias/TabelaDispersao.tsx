import { Fragment } from 'react'
import { Link } from 'react-router-dom'
import { CabecalhosEstatisticas, CelulasEstatisticas } from '../../componentes/colunasEstatisticas'
import { NUM_COLUNAS_ESTATISTICAS, valorEstatistica } from '../../componentes/estatisticas'
import { Cabecalho } from '../../componentes/Cabecalho'
import { escalaDe } from '../../componentes/escala'
import { ordenar, useOrdenacao } from '../../componentes/ordenacao'
import type { EstatisticasLoja, Subcategoria } from '../../tipos'
import { useLinkCategoria } from './rotas'

const todas = (lojas: EstatisticasLoja[]) => lojas.find((l) => l.loja_id === null) ?? lojas[0]

/**
 * Subcategorias do nó, cada uma com uma linha por loja e "Todas as lojas".
 * A ordenação dos grupos usa a linha "Todas as lojas"; dentro do grupo, as lojas seguem a mesma coluna.
 */
export function TabelaDispersao({ subcategorias }: { subcategorias: Subcategoria[] }) {
  const { ordenacao, alternar } = useOrdenacao()
  const link = useLinkCategoria()

  const grupos = ordenar(subcategorias, ordenacao, (s, chave) =>
    chave === 'rotulo' ? s.rotulo : valorEstatistica(todas(s.lojas).estatisticas, chave),
  )

  return (
    <div className="overflow-x-auto rounded-md border border-stone-300 bg-white">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <Cabecalho chave="rotulo" ordenacao={ordenacao} aoOrdenar={alternar} className="min-w-64">
              Categoria / loja
            </Cabecalho>
            <CabecalhosEstatisticas ordenacao={ordenacao} aoOrdenar={alternar} />
          </tr>
        </thead>
        <tbody>
          {grupos.map((s) => {
            // Escala comum ao grupo: as lojas de uma subcategoria ficam comparáveis entre si.
            const escala = escalaDe(s.lojas.map((l) => l.estatisticas))
            const porLoja = ordenar(
              s.lojas.filter((l) => l.loja_id !== null),
              ordenacao.chave === 'rotulo' ? { chave: null, direcao: 'asc' } : ordenacao,
              (l, chave) => valorEstatistica(l.estatisticas, chave),
            )
            const linhas = porLoja.length > 1 ? [...porLoja, todas(s.lojas)] : porLoja
            return (
              <Fragment key={s.caminho.join('/')}>
                <tr className="border-t-2 border-stone-300 bg-stone-50">
                  <td colSpan={NUM_COLUNAS_ESTATISTICAS + 1} className="px-2 py-1.5">
                    <Link to={link(s.caminho, 'produtos')} className="font-semibold hover:underline" title="Ver produtos">
                      {s.rotulo}
                    </Link>
                    {s.tem_filhos && (
                      <Link to={link(s.caminho)} className="ml-3 text-xs text-stone-600 underline">
                        subcategorias
                      </Link>
                    )}
                  </td>
                </tr>
                {linhas.map((l) => (
                  <tr
                    key={l.loja_id ?? 'todas'}
                    className={`border-b border-stone-200 hover:bg-amber-50 ${l.loja_id === null ? 'font-medium' : ''}`}
                  >
                    <td className="py-1.5 pr-2 pl-6">
                      <Link to={link(s.caminho, 'produtos')} className="hover:underline">
                        {l.loja}
                      </Link>
                    </td>
                    <CelulasEstatisticas estatisticas={l.estatisticas} escala={escala} />
                  </tr>
                ))}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
