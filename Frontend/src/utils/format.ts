export function formatMoney(amount: string | number, currency = 'EUR'): string {
  return new Intl.NumberFormat('en', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(Number(amount))
}
