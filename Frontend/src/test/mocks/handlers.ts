import { http, HttpResponse } from 'msw'
import {
  mockInvoices, mockJobs, mockTransactions, mockMatches,
  mockVendors, mockMissingInvoiceAlerts,
  mockSpendSummary, mockCategorySpend, mockVendorSpend, mockVatBreakdown, mockMomComparison,
  mockChatMessages,
} from './data.ts'
import type {
  InvoiceList,
  JobList,
  JobRead,
  TransactionList,
  MatchList,
  MatchRead,
  StatementUploadResponse,
  MatchTriggerResponse,
  VendorList,
  VendorRead,
  MissingInvoiceAlertList,
  ReportMeta,
  ChatHistory,
  ChatClearResponse,
} from '../../api/types/index.ts'

export const handlers = [
  // ── Invoices ──
  http.get('http://localhost:3000/api/invoices', ({ request }) => {
    const url = new URL(request.url)
    const status = url.searchParams.get('status')
    const skip = Number(url.searchParams.get('skip') ?? '0')
    const limit = Number(url.searchParams.get('limit') ?? '50')

    let filtered = mockInvoices
    if (status) {
      filtered = filtered.filter((inv) => inv.status === status)
    }

    const items = filtered.slice(skip, skip + limit)
    return HttpResponse.json({
      items,
      total: filtered.length,
    } satisfies InvoiceList)
  }),

  http.get('http://localhost:3000/api/invoices/:id', ({ params }) => {
    const invoice = mockInvoices.find((inv) => inv.id === params.id)
    if (!invoice) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(invoice)
  }),

  // ── Jobs ──
  http.get('http://localhost:3000/api/jobs', ({ request }) => {
    const url = new URL(request.url)
    const jobType = url.searchParams.get('job_type')
    const skip = Number(url.searchParams.get('skip') ?? '0')
    const limit = Number(url.searchParams.get('limit') ?? '20')

    let filtered = mockJobs
    if (jobType) {
      filtered = filtered.filter((job) => job.job_type === jobType)
    }

    const items = filtered.slice(skip, skip + limit)
    return HttpResponse.json({
      items,
      total: filtered.length,
    } satisfies JobList)
  }),

  http.get('http://localhost:3000/api/jobs/:id', ({ params }) => {
    const job = mockJobs.find((j) => j.id === params.id)
    if (!job) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(job)
  }),

  http.post('http://localhost:3000/api/jobs', async ({ request }) => {
    const body = (await request.json()) as { job_type: string }
    const newJob: JobRead = {
      id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
      job_type: body.job_type as JobRead['job_type'],
      status: 'running',
      triggered_by: 'user',
      started_at: new Date().toISOString(),
    }
    return HttpResponse.json(newJob, { status: 201 })
  }),

  // ── Reconciliation ──
  http.post('http://localhost:3000/api/reconciliation/upload', () => {
    return HttpResponse.json({
      transactions_parsed: 12,
      period: '2026-03',
    } satisfies StatementUploadResponse, { status: 201 })
  }),

  http.get('http://localhost:3000/api/reconciliation/transactions', ({ request }) => {
    const url = new URL(request.url)
    const period = url.searchParams.get('period')
    const status = url.searchParams.get('status')
    const skip = Number(url.searchParams.get('skip') ?? '0')
    const limit = Number(url.searchParams.get('limit') ?? '50')

    let filtered = mockTransactions
    if (period) filtered = filtered.filter((tx) => tx.period === period)
    if (status) filtered = filtered.filter((tx) => tx.status === status)

    const items = filtered.slice(skip, skip + limit)
    return HttpResponse.json({
      items,
      total: filtered.length,
    } satisfies TransactionList)
  }),

  http.post('http://localhost:3000/api/reconciliation/match', async ({ request }) => {
    const body = (await request.json()) as { period: string }
    return HttpResponse.json({
      matches_suggested: 3,
      period: body.period,
    } satisfies MatchTriggerResponse)
  }),

  http.get('http://localhost:3000/api/reconciliation/matches', ({ request }) => {
    const url = new URL(request.url)
    const period = url.searchParams.get('period')
    const skip = Number(url.searchParams.get('skip') ?? '0')
    const limit = Number(url.searchParams.get('limit') ?? '50')

    const filtered = period
      ? mockMatches
      : mockMatches
    const items = filtered.slice(skip, skip + limit)
    return HttpResponse.json({
      items,
      total: filtered.length,
    } satisfies MatchList)
  }),

  http.get('http://localhost:3000/api/reconciliation/matches/:matchId', ({ params }) => {
    const match = mockMatches.find((m) => m.id === params.matchId)
    if (!match) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json(match)
  }),

  http.post('http://localhost:3000/api/reconciliation/matches/:matchId/confirm', ({ params }) => {
    const match = mockMatches.find((m) => m.id === params.matchId)
    if (!match) return new HttpResponse(null, { status: 404 })
    const confirmed: MatchRead = {
      ...match,
      confirmed_by: 'user',
      confirmed_at: new Date().toISOString(),
    }
    return HttpResponse.json(confirmed)
  }),

  http.delete('http://localhost:3000/api/reconciliation/matches/:matchId', ({ params }) => {
    const match = mockMatches.find((m) => m.id === params.matchId)
    if (!match) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json(match)
  }),

  http.patch('http://localhost:3000/api/reconciliation/matches/:matchId/reassign', async ({ params, request }) => {
    const match = mockMatches.find((m) => m.id === params.matchId)
    if (!match) return new HttpResponse(null, { status: 404 })
    const body = (await request.json()) as { invoice_id?: string; transaction_id?: string }
    const reassigned: MatchRead = {
      ...match,
      invoice_id: body.invoice_id ?? match.invoice_id,
      transaction_id: body.transaction_id ?? match.transaction_id,
    }
    return HttpResponse.json(reassigned)
  }),

  // ── Vendors ──
  http.get('http://localhost:3000/api/vendors', ({ request }) => {
    const url = new URL(request.url)
    const skip = Number(url.searchParams.get('skip') ?? '0')
    const limit = Number(url.searchParams.get('limit') ?? '50')
    const items = mockVendors.slice(skip, skip + limit)
    return HttpResponse.json({
      items,
      total: mockVendors.length,
    } satisfies VendorList)
  }),

  http.get('http://localhost:3000/api/vendors/:vendorId/invoices', ({ params, request }) => {
    const url = new URL(request.url)
    const skip = Number(url.searchParams.get('skip') ?? '0')
    const limit = Number(url.searchParams.get('limit') ?? '50')
    const vendor = mockVendors.find((v) => v.id === params.vendorId)
    if (!vendor) return new HttpResponse(null, { status: 404 })
    const invoices = mockInvoices.filter((inv) => inv.vendor === vendor.name)
    const items = invoices.slice(skip, skip + limit)
    return HttpResponse.json({
      items,
      total: invoices.length,
    } satisfies InvoiceList)
  }),

  http.get('http://localhost:3000/api/vendors/:vendorId', ({ params }) => {
    const vendor = mockVendors.find((v) => v.id === params.vendorId)
    if (!vendor) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json(vendor)
  }),

  http.post('http://localhost:3000/api/vendors', async ({ request }) => {
    const body = (await request.json()) as VendorRead
    const newVendor: VendorRead = {
      id: 'v-new-0000-0000-0000-000000000000',
      name: body.name,
      aliases: body.aliases ?? null,
      default_category: body.default_category ?? null,
      default_vat_rate: body.default_vat_rate ?? null,
      billing_cycle: body.billing_cycle ?? 'monthly',
    }
    return HttpResponse.json(newVendor, { status: 201 })
  }),

  http.patch('http://localhost:3000/api/vendors/:vendorId', async ({ params, request }) => {
    const vendor = mockVendors.find((v) => v.id === params.vendorId)
    if (!vendor) return new HttpResponse(null, { status: 404 })
    const body = (await request.json()) as Partial<VendorRead>
    return HttpResponse.json({ ...vendor, ...body })
  }),

  http.delete('http://localhost:3000/api/vendors/:vendorId', ({ params }) => {
    const vendor = mockVendors.find((v) => v.id === params.vendorId)
    if (!vendor) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json(vendor)
  }),

  // ── Dashboard ──
  http.get('http://localhost:3000/api/dashboard/missing-invoices', () => {
    return HttpResponse.json({
      items: mockMissingInvoiceAlerts,
      total: mockMissingInvoiceAlerts.length,
    } satisfies MissingInvoiceAlertList)
  }),

  http.get('http://localhost:3000/api/dashboard/spend-summary', () => {
    return HttpResponse.json(mockSpendSummary)
  }),

  http.get('http://localhost:3000/api/dashboard/spend-by-category', () => {
    return HttpResponse.json({ items: mockCategorySpend })
  }),

  http.get('http://localhost:3000/api/dashboard/spend-by-vendor', () => {
    return HttpResponse.json({ items: mockVendorSpend })
  }),

  http.get('http://localhost:3000/api/dashboard/vat-summary', () => {
    return HttpResponse.json({ items: mockVatBreakdown })
  }),

  http.get('http://localhost:3000/api/dashboard/mom-comparison', () => {
    return HttpResponse.json({ items: mockMomComparison })
  }),

  http.get('http://localhost:3000/api/dashboard/tax-summary', () => {
    return HttpResponse.json({ total_amount: '0.00', transaction_count: 0, by_category: [] })
  }),

  http.get('http://localhost:3000/api/dashboard/earnings', () => {
    return HttpResponse.json({ total_earnings: '0.00', transaction_count: 0, by_category: [] })
  }),

  http.get('http://localhost:3000/api/dashboard/withholdings', () => {
    return HttpResponse.json({ total_withheld: '0.00', transaction_count: 0, by_category: [] })
  }),

  http.get('http://localhost:3000/api/reconciliation/overview', () => {
    return HttpResponse.json({
      period: '2026-03',
      invoice_count: 3,
      matched_invoice_count: 1,
      invoiced_total: '97.40',
      transaction_count: 3,
      matched_transaction_count: 1,
      bank_debits: '157.88',
      earnings: '0.00',
      earnings_count: 0,
      gap: '60.48',
      no_invoice_expenses: '75.00',
      no_invoice_expense_count: 1,
      owner_withdrawals: '0.00',
      owner_withdrawal_count: 0,
      unmatched_invoice_list: [],
      unmatched_transaction_list: [],
      withholding_total: '0.00',
      withholding_count: 0,
    })
  }),

  // ── Reports ──
  http.post('http://localhost:3000/api/reports/preview', async ({ request }) => {
    const body = (await request.json()) as { timeframe: string; format: string }
    return HttpResponse.json({
      timeframe_label: `${body.timeframe} report`,
      periods: ['2026-03'],
      format: body.format as ReportMeta['format'],
      filename: `openreconfi-report-2026-03.${body.format === 'pdf' ? 'pdf' : 'xlsx'}`,
    } satisfies ReportMeta)
  }),

  http.post('http://localhost:3000/api/reports/generate', () => {
    return new HttpResponse(new Blob(['mock report content']), {
      status: 200,
      headers: {
        'Content-Type': 'application/octet-stream',
        'Content-Disposition': 'attachment; filename="openreconfi-report.pdf"',
      },
    })
  }),

  // ── Categories ──
  http.get('http://localhost:3000/api/categories', () => {
    return HttpResponse.json([
      { id: 'cat-1', name: 'SaaS', color: 'blue' },
      { id: 'cat-2', name: 'Hosting', color: 'green' },
      { id: 'cat-3', name: 'Design', color: 'purple' },
    ])
  }),

  // ── Chat ──
  http.get('http://localhost:3000/api/chat/suggestions', () => {
    return HttpResponse.json({
      questions: [
        'What are my top vendors?',
        'Show me unmatched invoices',
        'VAT summary this quarter',
      ],
    })
  }),

  http.get('http://localhost:3000/api/chat/history', () => {
    return HttpResponse.json({
      items: mockChatMessages,
      total: mockChatMessages.length,
    } satisfies ChatHistory)
  }),

  http.post('http://localhost:3000/api/chat/message', async ({ request }) => {
    const body = (await request.json()) as { message: string }
    const responseText = `You asked: "${body.message}". Based on your expense data, here is a helpful answer with insights about your spending patterns.`

    const chunks = [
      `data: ${JSON.stringify({ content: responseText.slice(0, 40) })}\n\n`,
      `data: ${JSON.stringify({ content: responseText.slice(40, 80) })}\n\n`,
      `data: ${JSON.stringify({ content: responseText.slice(80), retrieved_invoice_ids: ['11111111-1111-1111-1111-111111111111'] })}\n\n`,
      'data: [DONE]\n\n',
    ]

    const stream = new ReadableStream({
      start(controller) {
        const encoder = new TextEncoder()
        for (const chunk of chunks) {
          controller.enqueue(encoder.encode(chunk))
        }
        controller.close()
      },
    })

    return new HttpResponse(stream, {
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
    })
  }),

  http.delete('http://localhost:3000/api/chat/history', () => {
    return HttpResponse.json({ deleted: 2 } satisfies ChatClearResponse)
  }),
]
