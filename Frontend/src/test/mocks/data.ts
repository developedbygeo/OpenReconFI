import type {
  InvoiceRead, JobRead, TransactionRead, MatchRead,
  VendorRead, MissingInvoiceAlert,
  SpendSummary, CategorySpend, VendorSpend, VATBreakdown, MonthlySpend,
  ChatMessageRead,
} from '../../api/types/index.ts'

export const mockInvoices: InvoiceRead[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    vendor: 'Vercel Inc.',
    amount_excl: '40.50',
    amount_incl: '49.00',
    vat_amount: '8.50',
    vat_rate: '21.00',
    invoice_date: '2026-03-01',
    invoice_number: 'INV-2026-0312',
    category: 'SaaS',
    drive_url: 'https://drive.google.com/file/d/abc123',
    drive_file_id: 'abc123',
    source: 'gmail',
    status: 'pending',
    period: '2026-03',
    currency: 'EUR',
    raw_extraction: { vendor: 'Vercel Inc.', confidence: 0.98 },
    created_at: '2026-03-02T10:00:00Z',
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    vendor: 'Hetzner Online',
    amount_excl: '28.00',
    amount_incl: '33.88',
    vat_amount: '5.88',
    vat_rate: '21.00',
    invoice_date: '2026-03-05',
    invoice_number: 'H-2026-0305',
    category: 'Hosting',
    drive_url: null,
    drive_file_id: null,
    source: 'manual',
    status: 'matched',
    period: '2026-03',
    currency: 'EUR',
    created_at: '2026-03-06T09:30:00Z',
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    vendor: 'Figma Inc.',
    amount_excl: '12.00',
    amount_incl: '14.52',
    vat_amount: '2.52',
    vat_rate: '21.00',
    invoice_date: '2026-02-28',
    invoice_number: 'FIG-0228',
    category: 'Design',
    drive_url: 'https://drive.google.com/file/d/xyz789',
    drive_file_id: 'xyz789',
    source: 'gmail',
    status: 'unmatched',
    period: '2026-02',
    currency: 'EUR',
    created_at: '2026-03-01T08:00:00Z',
  },
]

export const mockJobs: JobRead[] = [
  {
    id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    job_type: 'gmail_sync',
    status: 'done',
    triggered_by: 'user',
    started_at: '2026-03-20T14:00:00Z',
    finished_at: '2026-03-20T14:02:30Z',
    summary: { emails_processed: 5, invoices_created: 3 },
  },
  {
    id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    job_type: 'gmail_sync',
    status: 'failed',
    triggered_by: 'user',
    started_at: '2026-03-19T10:00:00Z',
    finished_at: '2026-03-19T10:00:05Z',
    summary: { error: 'Gmail API quota exceeded' },
  },
]

export const mockTransactions: TransactionRead[] = [
  {
    id: 'tx-111111-1111-1111-1111-111111111111',
    tx_date: '2026-03-04',
    amount: '-49.00',
    description: 'VERCEL INC SUBSCRIPTION',
    counterparty: 'Vercel Inc',
    counterparty_iban: 'NL02ABNA0123456789',
    period: '2026-03',
    status: 'unmatched',
  },
  {
    id: 'tx-222222-2222-2222-2222-222222222222',
    tx_date: '2026-03-06',
    amount: '-33.88',
    description: 'HETZNER ONLINE GMBH SERVER',
    counterparty: 'Hetzner Online GmbH',
    counterparty_iban: 'DE89370400440532013000',
    period: '2026-03',
    status: 'matched',
  },
  {
    id: 'tx-333333-3333-3333-3333-333333333333',
    tx_date: '2026-03-10',
    amount: '-75.00',
    description: 'UNKNOWN VENDOR PAYMENT',
    counterparty: 'Unknown Corp',
    counterparty_iban: null,
    period: '2026-03',
    status: 'unmatched',
  },
]

export const mockMatches: MatchRead[] = [
  {
    id: 'match-1111-1111-1111-111111111111',
    invoice_id: '11111111-1111-1111-1111-111111111111',
    transaction_id: 'tx-111111-1111-1111-1111-111111111111',
    confidence: '0.97',
    rationale: 'Amount matches exactly (€49.00). Date within 3 days. "VERCEL INC" in bank description matches vendor name.',
    confirmed_by: 'llm',
    confirmed_at: null,
  },
  {
    id: 'match-2222-2222-2222-222222222222',
    invoice_id: '22222222-2222-2222-2222-222222222222',
    transaction_id: 'tx-222222-2222-2222-2222-222222222222',
    confidence: '0.92',
    rationale: 'Amount matches exactly (€33.88). "HETZNER" appears in both vendor and bank description.',
    confirmed_by: 'user',
    confirmed_at: '2026-03-20T15:00:00Z',
  },
  {
    id: 'match-3333-3333-3333-333333333333',
    invoice_id: '33333333-3333-3333-3333-333333333333',
    transaction_id: 'tx-333333-3333-3333-3333-333333333333',
    confidence: '0.35',
    rationale: 'Amount does not match. Vendor name not found in bank description. Low confidence — likely not a match.',
    confirmed_by: 'llm',
    confirmed_at: null,
  },
]

export const mockVendors: VendorRead[] = [
  {
    id: 'v-111111-1111-1111-1111-111111111111',
    name: 'Vercel Inc.',
    aliases: ['VERCEL INC', 'VERCEL INC SUBSCRIPTION'],
    default_category: 'SaaS',
    default_vat_rate: '21.00',
    billing_cycle: 'monthly',
  },
  {
    id: 'v-222222-2222-2222-2222-222222222222',
    name: 'Hetzner Online',
    aliases: ['HETZNER ONLINE GMBH', 'HETZNER ONLINE GMBH SERVER'],
    default_category: 'Hosting',
    default_vat_rate: '21.00',
    billing_cycle: 'monthly',
  },
  {
    id: 'v-333333-3333-3333-3333-333333333333',
    name: 'Figma Inc.',
    aliases: null,
    default_category: 'Design',
    default_vat_rate: '21.00',
    billing_cycle: 'annual',
  },
]

export const mockMissingInvoiceAlerts: MissingInvoiceAlert[] = [
  {
    vendor_id: 'v-222222-2222-2222-2222-222222222222',
    vendor_name: 'Hetzner Online',
    billing_cycle: 'monthly',
    last_invoice_period: '2026-02',
    expected_period: '2026-03',
  },
]

export const mockSpendSummary: SpendSummary = {
  total_spend_excl: '80.50',
  total_vat: '16.90',
  total_spend_incl: '97.40',
  invoice_count: 3,
  matched_count: 1,
  unmatched_count: 2,
}

export const mockCategorySpend: CategorySpend[] = [
  { category: 'SaaS', total_excl: '40.50', total_vat: '8.50', total_incl: '49.00', invoice_count: 1 },
  { category: 'Hosting', total_excl: '28.00', total_vat: '5.88', total_incl: '33.88', invoice_count: 1 },
  { category: 'Design', total_excl: '12.00', total_vat: '2.52', total_incl: '14.52', invoice_count: 1 },
]

export const mockVendorSpend: VendorSpend[] = [
  { vendor: 'Vercel Inc.', total_excl: '40.50', total_vat: '8.50', total_incl: '49.00', invoice_count: 1 },
  { vendor: 'Hetzner Online', total_excl: '28.00', total_vat: '5.88', total_incl: '33.88', invoice_count: 1 },
  { vendor: 'Figma Inc.', total_excl: '12.00', total_vat: '2.52', total_incl: '14.52', invoice_count: 1 },
]

export const mockVatBreakdown: VATBreakdown[] = [
  { vat_rate: '21.00', total_excl: '80.50', total_vat: '16.90', invoice_count: 3 },
]

export const mockMomComparison: MonthlySpend[] = [
  { period: '2026-01', total_excl: '60.00', total_vat: '12.60', total_incl: '72.60', invoice_count: 2 },
  { period: '2026-02', total_excl: '45.00', total_vat: '9.45', total_incl: '54.45', invoice_count: 2 },
  { period: '2026-03', total_excl: '80.50', total_vat: '16.90', total_incl: '97.40', invoice_count: 3 },
]

export const mockChatMessages: ChatMessageRead[] = [
  {
    id: 'chat-1111-1111-1111-111111111111',
    role: 'user',
    content: 'What are my top 5 vendors by spend?',
    created_at: '2026-03-20T16:00:00Z',
  },
  {
    id: 'chat-2222-2222-2222-222222222222',
    role: 'assistant',
    content: 'Based on your invoices, here are your top vendors by total spend (incl. VAT):\n\n1. **Vercel Inc.** — €49.00 (1 invoice)\n2. **Hetzner Online** — €33.88 (1 invoice)\n3. **Figma Inc.** — €14.52 (1 invoice)\n\nVercel is your largest expense this period.',
    retrieved_invoice_ids: ['11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222'],
    retrieved_tx_ids: null,
    created_at: '2026-03-20T16:00:05Z',
  },
]
