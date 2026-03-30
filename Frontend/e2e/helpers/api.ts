const BASE = 'http://localhost:3000/api'

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${method} ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  createVendor(data: {
    name: string
    billing_cycle?: string
    default_category?: string | null
    default_vat_rate?: string | null
    aliases?: string[] | null
  }) {
    return request<{ id: string; name: string }>('POST', '/vendors', {
      billing_cycle: 'monthly',
      ...data,
    })
  },

  deleteVendor(id: string) {
    return request('DELETE', `/vendors/${id}`)
  },

  listVendors() {
    return request<{ items: { id: string; name: string }[]; total: number }>('GET', '/vendors?limit=100')
  },

  listInvoices() {
    return request<{ items: { id: string; vendor: string }[]; total: number }>('GET', '/invoices?limit=100')
  },
}
