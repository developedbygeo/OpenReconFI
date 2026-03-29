import {
  Stack,
  Button,
  Modal,
  Select,
} from '@mantine/core'
import type { InvoiceRead, TransactionRead } from '../../../api/types/index.ts'
import { formatMoney } from '../../../utils/format.ts'

export function ReassignModal({
  opened,
  onClose,
  invoices,
  transactions,
  newInvoiceId,
  setNewInvoiceId,
  newTransactionId,
  setNewTransactionId,
  onReassign,
}: {
  opened: boolean
  onClose: () => void
  invoices: InvoiceRead[]
  transactions: TransactionRead[]
  newInvoiceId: string | null
  setNewInvoiceId: (v: string | null) => void
  newTransactionId: string | null
  setNewTransactionId: (v: string | null) => void
  onReassign: () => void
}) {
  return (
    <Modal opened={opened} onClose={onClose} title="Reassign Match">
      <Stack>
        <Select
          label="Invoice"
          data={invoices.map((inv) => ({
            value: inv.id,
            label: `${inv.vendor} — ${formatMoney(inv.amount_incl, inv.currency)} (${inv.invoice_number})`,
          }))}
          value={newInvoiceId}
          onChange={setNewInvoiceId}
          searchable
        />
        <Select
          label="Transaction"
          data={transactions.map((tx) => ({
            value: tx.id,
            label: `${tx.counterparty} — ${formatMoney(tx.amount)} (${tx.tx_date})`,
          }))}
          value={newTransactionId}
          onChange={setNewTransactionId}
          searchable
        />
        <Button onClick={onReassign}>Save</Button>
      </Stack>
    </Modal>
  )
}
