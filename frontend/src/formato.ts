const moedaFmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const inteiroFmt = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })
const pctFmt = new Intl.NumberFormat('pt-BR', { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 })
const decimalFmt = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const VAZIO = '–'

export const moeda = (v: number | null | undefined) => (v === null || v === undefined ? VAZIO : moedaFmt.format(v))
export const inteiro = (v: number | null | undefined) => (v === null || v === undefined ? VAZIO : inteiroFmt.format(v))
export const pct = (v: number | null | undefined) => (v === null || v === undefined ? VAZIO : pctFmt.format(v))
export const decimal = (v: number | null | undefined) => (v === null || v === undefined ? VAZIO : decimalFmt.format(v))
