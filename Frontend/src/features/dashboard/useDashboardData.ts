import { useState, useEffect, useRef } from 'react'
import type {
  SpendSummary,
  CategorySpendList,
  VendorSpendList,
  VATSummary,
  MoMComparison,
  MonthlySpend,
  TaxSummary,
  EarningsSummary,
  WithholdingsSummary,
} from '../../api/types/index.ts'

interface DashboardData {
  summary?: SpendSummary
  byCategory?: CategorySpendList
  byVendor?: VendorSpendList
  vat?: VATSummary
  mom?: MoMComparison
  tax?: TaxSummary
  earnings?: EarningsSummary
  withholdings?: WithholdingsSummary
  isLoading: boolean
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`fetch ${url} failed`)
  return res.json() as Promise<T>
}

function sumSummaries(items: SpendSummary[]): SpendSummary {
  return items.reduce<SpendSummary>(
    (acc, s) => ({
      total_spend_excl: (parseFloat(acc.total_spend_excl) + parseFloat(s.total_spend_excl)).toFixed(2),
      total_vat: (parseFloat(acc.total_vat) + parseFloat(s.total_vat)).toFixed(2),
      total_spend_incl: (parseFloat(acc.total_spend_incl) + parseFloat(s.total_spend_incl)).toFixed(2),
      invoice_count: acc.invoice_count + s.invoice_count,
      matched_count: acc.matched_count + s.matched_count,
      unmatched_count: acc.unmatched_count + s.unmatched_count,
    }),
    { total_spend_excl: '0', total_vat: '0', total_spend_incl: '0', invoice_count: 0, matched_count: 0, unmatched_count: 0 },
  )
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mergeByKey(
  items: any[][],
  key: string,
  numericFields: string[],
  countField: string,
): any[] {
  const map = new Map<string, any>()
  for (const list of items) {
    for (const item of list) {
      const k = item[key] as string
      const existing = map.get(k)
      if (existing) {
        const merged = { ...existing }
        for (const f of numericFields) {
          merged[f] = (parseFloat(existing[f]) + parseFloat(item[f])).toFixed(2)
        }
        merged[countField] = existing[countField] + item[countField]
        map.set(k, merged)
      } else {
        map.set(k, { ...item })
      }
    }
  }
  return Array.from(map.values())
}

function yearsFromPeriods(periods: string[]): number[] {
  const years = new Set(periods.map((p) => parseInt(p.split('-')[0], 10)))
  return Array.from(years).sort()
}

export function useDashboardData(periods: string[]): DashboardData {
  const [data, setData] = useState<DashboardData>({
    summary: undefined,
    byCategory: undefined,
    byVendor: undefined,
    vat: undefined,
    mom: undefined,
    tax: undefined,
    earnings: undefined,
    withholdings: undefined,
    isLoading: true,
  })
  const reqId = useRef(0)

  useEffect(() => {
    const id = ++reqId.current
    setData((prev) => ({ ...prev, isLoading: true }))

    const isSingle = periods.length === 1
    const isAll = periods.length === 0
    const isMulti = periods.length > 1

    const targets = isAll ? [''] : periods

    const dashboardFetches = Promise.all(
      targets.map((p) => {
        const qs = p ? `?period=${p}` : ''
        return Promise.all([
          fetchJson<SpendSummary>(`/api/dashboard/spend-summary${qs}`),
          fetchJson<CategorySpendList>(`/api/dashboard/spend-by-category${qs}`),
          fetchJson<VendorSpendList>(`/api/dashboard/spend-by-vendor${qs}`),
          fetchJson<VATSummary>(`/api/dashboard/vat-summary${qs}`),
          fetchJson<TaxSummary>(`/api/dashboard/tax-summary${qs}`).catch(() => null),
          fetchJson<EarningsSummary>(`/api/dashboard/earnings${qs}`).catch(() => null),
          fetchJson<WithholdingsSummary>(`/api/dashboard/withholdings${qs}`).catch(() => null),
        ])
      }),
    )

    const momFetch = isMulti
      ? Promise.resolve(null)
      : (() => {
          const years = isAll ? [new Date().getFullYear()] : yearsFromPeriods(periods)
          return fetchJson<MoMComparison>(`/api/dashboard/mom-comparison?year=${years[0]}`)
        })()

    Promise.all([dashboardFetches, momFetch]).then(([results, momData]) => {
      if (id !== reqId.current) return

      if (isSingle || isAll) {
        const [summary, byCategory, byVendor, vat, tax, earnings, withholdings] = results[0]
        setData({ summary, byCategory, byVendor, vat, tax: tax ?? undefined, earnings: earnings ?? undefined, withholdings: withholdings ?? undefined, mom: momData ?? undefined, isLoading: false })
        return
      }

      const summaries = results.map((r) => r[0])
      const categories = results.map((r) => r[1].items)
      const vendors = results.map((r) => r[2].items)
      const vats = results.map((r) => r[3].items)
      const taxes = results.map((r) => r[4]).filter(Boolean) as TaxSummary[]
      const earningsList = results.map((r) => r[5]).filter(Boolean) as EarningsSummary[]
      const withholdingsList = results.map((r) => r[6]).filter(Boolean) as WithholdingsSummary[]

      const momFromPeriods: MoMComparison = {
        items: periods.map((period, i): MonthlySpend => ({
          period,
          total_excl: summaries[i].total_spend_excl,
          total_vat: summaries[i].total_vat,
          total_incl: summaries[i].total_spend_incl,
          invoice_count: summaries[i].invoice_count,
        })),
      }

      setData({
        summary: sumSummaries(summaries),
        byCategory: {
          items: mergeByKey(categories, 'category', ['total_excl', 'total_vat', 'total_incl'], 'invoice_count'),
        },
        byVendor: {
          items: mergeByKey(vendors, 'vendor', ['total_excl', 'total_vat', 'total_incl'], 'invoice_count'),
        },
        vat: {
          items: mergeByKey(vats, 'vat_rate', ['total_excl', 'total_vat'], 'invoice_count'),
        },
        mom: momFromPeriods,
        tax: taxes.length > 0
          ? {
              period: periods.join(', '),
              total_amount: String(taxes.reduce((s, t) => s + Number(t.total_amount), 0)),
              transaction_count: taxes.reduce((s, t) => s + t.transaction_count, 0),
              by_category: mergeByKey(
                taxes.map((t) => t.by_category),
                'category', ['total_amount'], 'transaction_count',
              ),
              items: taxes.flatMap((t) => t.items),
            }
          : undefined,
        earnings: earningsList.length > 0
          ? {
              period: periods.join(', '),
              total_earnings: String(earningsList.reduce((s, e) => s + Number(e.total_earnings), 0)),
              transaction_count: earningsList.reduce((s, e) => s + e.transaction_count, 0),
              items: earningsList.flatMap((e) => e.items),
            }
          : undefined,
        withholdings: withholdingsList.length > 0
          ? {
              period: periods.join(', '),
              total_amount: String(withholdingsList.reduce((s, w) => s + Number(w.total_amount), 0)),
              transaction_count: withholdingsList.reduce((s, w) => s + w.transaction_count, 0),
              items: withholdingsList.flatMap((w) => w.items),
            }
          : undefined,
        isLoading: false,
      })
    }).catch(() => {
      if (id !== reqId.current) return
      setData((prev) => ({ ...prev, isLoading: false }))
    })
  }, [periods.join(',')])

  return data
}
