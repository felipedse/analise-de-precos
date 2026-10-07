/** Escala logarítmica de preços para as barras de faixa (preços são muito assimétricos). */
export interface Escala {
  minimo: number
  maximo: number
}

export function escalaDe(valores: { minimo: number | null; maximo: number | null }[]): Escala | null {
  const minimos = valores.map((v) => v.minimo).filter((v): v is number => v !== null && v > 0)
  const maximos = valores.map((v) => v.maximo).filter((v): v is number => v !== null && v > 0)
  if (!minimos.length || !maximos.length) return null
  return { minimo: Math.min(...minimos), maximo: Math.max(...maximos) }
}

/** Posição (0..largura) de um preço; valores fora da escala ficam presos às bordas. */
export function posicao(valor: number, escala: Escala, largura: number): number {
  const { minimo, maximo } = escala
  if (maximo <= minimo) return largura / 2
  const v = Math.min(Math.max(valor, minimo), maximo)
  return ((Math.log(v) - Math.log(minimo)) / (Math.log(maximo) - Math.log(minimo))) * largura
}
