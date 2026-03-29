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
  http.get('/api/invoices', ({ request }) => {
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

  http.get('/api/invoices/:id', ({ params }) => {
    const invoice = mockInvoices.find((inv) => inv.id === params.id)
    if (!invoice) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(invoice)
  }),

  // ── Jobs ──
  http.get('/api/jobs', ({ request }) => {
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

  http.get('/api/jobs/:id', ({ params }) => {
    const job = mockJobs.find((j) => j.id === params.id)
    if (!job) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(job)
  }),

  http.post('/api/jobs', async ({ request }) => {
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
  http.post('/api/reconciliation/upload', () => {
    return HttpResponse.json({
      transactions_parsed: 12,
      period: '2026-03',
    } satisfies StatementUploadResponse, { status: 201 })
  }),

  http.get('/api/reconciliation/transactions', ({ request }) => {
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

  http.post('/api/reconciliation/match', async ({ request }) => {
    const body = (await request.json()) as { period: string }
    return HttpResponse.json({
      matches_suggested: 3,
      period: body.period,
    } satisfies MatchTriggerResponse)
  }),

  http.get('/api/reconciliation/matches', ({ request }) => {
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

  http.get('/api/reconciliation/matches/:matchId', ({ params }) => {
    const match = mockMatches.find((m) => m.id === params.matchId)
    if (!match) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json(match)
  }),

  http.post('/api/reconciliation/matches/:matchId/confirm', ({ params }) => {
    const match = mockMatches.find((m) => m.id === params.matchId)
    if (!match) return new HttpResponse(null, { status: 404 })
    const confirmed: MatchRead = {
      ...match,
      confirmed_by: 'user',
      confirmed_at: new Date().toISOString(),
    }
    return HttpResponse.json(confirmed)
  }),

  http.delete('/api/reconciliation/matches/:matchId', ({ params }) => {
    const match = mockMatches.find((m) => m.id === params.matchId)
    if (!match) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json(match)
  }),

  http.patch('/api/reconciliation/matches/:matchId/reassign', async ({ params, request }) => {
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
  http.get('/api/vendors', ({ request }) => {
    const url = new URL(request.url)
    const skip = Number(url.searchParams.get('skip') ?? '0')
    const limit = Number(url.searchParams.get('limit') ?? '50')
    const items = mockVendors.slice(skip, skip + limit)
    return HttpResponse.json({
      items,
      total: mockVendors.length,
    } satisfies VendorList)
  }),

  http.get('/api/vendors/:vendorId/invoices', ({ params, request }) => {
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

  http.get('/api/vendors/:vendorId', ({ params }) => {
    const vendor = mockVendors.find((v) => v.id === params.vendorId)
    if (!vendor) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json(vendor)
  }),

  http.post('/api/vendors', async ({ request }) => {
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

  http.patch('/api/vendors/:vendorId', async ({ params, request }) => {
    const vendor = mockVendors.find((v) => v.id === params.vendorId)
    if (!vendor) return new HttpResponse(null, { status: 404 })
    const body = (await request.json()) as Partial<VendorRead>
    return HttpResponse.json({ ...vendor, ...body })
  }),

  http.delete('/api/vendors/:vendorId', ({ params }) => {
    const vendor = mockVendors.find((v) => v.id === params.vendorId)
    if (!vendor) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json(vendor)
  }),

  // ── Dashboard ──
  http.get('/api/dashboard/missing-invoices', () => {
    return HttpResponse.json({
      items: mockMissingInvoiceAlerts,
      total: mockMissingInvoiceAlerts.length,
    } satisfies MissingInvoiceAlertList)
  }),

  http.get('/api/dashboard/spend-summary', () => {
    return HttpResponse.json(mockSpendSummary)
  }),

  http.get('/api/dashboard/spend-by-category', () => {
    return HttpResponse.json({ items: mockCategorySpend })
  }),

  http.get('/api/dashboard/spend-by-vendor', () => {
    return HttpResponse.json({ items: mockVendorSpend })
  }),

  http.get('/api/dashboard/vat-summary', () => {
    return HttpResponse.json({ items: mockVatBreakdown })
  }),

  http.get('/api/dashboard/mom-comparison', () => {
    return HttpResponse.json({ items: mockMomComparison })
  }),

  // ── Reports ──
  http.post('/api/reports/preview', async ({ request }) => {
    const body = (await request.json()) as { timeframe: string; format: string }
    return HttpResponse.json({
      timeframe_label: `${body.timeframe} report`,
      periods: ['2026-03'],
      format: body.format as ReportMeta['format'],
      filename: `openreconfi-report-2026-03.${body.format === 'pdf' ? 'pdf' : 'xlsx'}`,
    } satisfies ReportMeta)
  }),

  http.post('/api/reports/generate', () => {
    return new HttpResponse(new Blob(['mock report content']), {
      status: 200,
      headers: {
        'Content-Type': 'application/octet-stream',
        'Content-Disposition': 'attachment; filename="openreconfi-report.pdf"',
      },
    })
  }),

  // ── Chat ──
  http.get('/api/chat/history', () => {
    return HttpResponse.json({
      items: mockChatMessages,
      total: mockChatMessages.length,
    } satisfies ChatHistory)
  }),

  http.post('/api/chat/message', async ({ request }) => {
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

  http.delete('/api/chat/history', () => {
    return HttpResponse.json({ deleted: 2 } satisfies ChatClearResponse)
  }),
]
