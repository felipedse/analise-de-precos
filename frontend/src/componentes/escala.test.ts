import { describe, expect, it } from 'vitest'
import { escalaDe, posicao } from './escala'
import { ordenar, proximaOrdenacao } from './ordenacao'

describe('escala log', () => {
  const escala = { minimo: 1, maximo: 100 }

  it('posiciona em log', () => {
    expect(posicao(1, escala, 100)).toBe(0)
    expect(posicao(10, escala, 100)).toBeCloseTo(50)
    expect(posicao(100, escala, 100)).toBe(100)
  })

  it('prende valores fora da escala (inclusive média − σ negativa)', () => {
    expect(posicao(-5, escala, 100)).toBe(0)
    expect(posicao(1000, escala, 100)).toBe(100)
  })

  it('usa o menor mínimo e o maior máximo, ignorando nulos', () => {
    expect(escalaDe([{ minimo: 2, maximo: 10 }, { minimo: 1, maximo: 50 }, { minimo: null, maximo: null }])).toEqual({
      minimo: 1,
      maximo: 50,
    })
    expect(escalaDe([{ minimo: null, maximo: null }])).toBeNull()
  })
})

describe('ordenação', () => {
  it('cicla crescente → decrescente → sem ordenação', () => {
    let o = proximaOrdenacao({ chave: null, direcao: 'asc' }, 'n')
    expect(o).toEqual({ chave: 'n', direcao: 'asc' })
    o = proximaOrdenacao(o, 'n')
    expect(o).toEqual({ chave: 'n', direcao: 'desc' })
    expect(proximaOrdenacao(o, 'n').chave).toBeNull()
  })

  it('deixa nulos no fim nas duas direções', () => {
    const itens = [{ v: 2 }, { v: null }, { v: 1 }]
    const valor = (i: { v: number | null }) => i.v
    expect(ordenar(itens, { chave: 'v', direcao: 'asc' }, valor).map((i) => i.v)).toEqual([1, 2, null])
    expect(ordenar(itens, { chave: 'v', direcao: 'desc' }, valor).map((i) => i.v)).toEqual([2, 1, null])
  })

  it('compara texto em pt-BR', () => {
    const itens = ['Óleos', 'Arroz', 'Café']
    expect(ordenar(itens, { chave: 'x', direcao: 'asc' }, (i) => i)).toEqual(['Arroz', 'Café', 'Óleos'])
  })
})
