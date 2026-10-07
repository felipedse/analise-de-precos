import { describe, expect, it } from 'vitest'
import { moeda, pct } from './formato'

describe('formato', () => {
  it('formata moeda e percentual em pt-BR', () => {
    expect(moeda(1234.5).replace(/\s/g, ' ')).toBe('R$ 1.234,50')
    expect(pct(0.1234)).toBe('12,3%')
    expect(moeda(null)).toBe('–')
  })
})
