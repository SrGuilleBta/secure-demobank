// Montos: la API trabaja en centavos enteros (2500 = $25.00). Aquí se convierte sin usar decimales flotantes.

const MAX_CENTS = 1_000_000 // mismo tope que el backend (schemas.py: le=1_000_000)

const formatter = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' })

export function formatCents(cents) {
  return formatter.format(cents / 100)
}

// "25", "25.5", "25,50" -> 2550. Devuelve null si el texto no es un monto válido.
export function parseAmountToCents(text) {
  const match = /^(\d{1,7})(?:[.,](\d{1,2}))?$/.exec(text.trim())
  if (!match) return null
  const cents = Number(match[1]) * 100 + Number((match[2] ?? '').padEnd(2, '0'))
  if (cents <= 0 || cents > MAX_CENTS) return null
  return cents
}

export const MAX_AMOUNT_TEXT = formatCents(MAX_CENTS)

export function formatDate(iso) {
  return new Date(iso).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' })
}
