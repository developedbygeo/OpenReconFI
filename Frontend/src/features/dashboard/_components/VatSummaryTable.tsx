import {
  Card,
  Title,
  Table,
} from '@mantine/core'
import type { VATSummary } from '../../../api/types/index.ts'

export function VatSummaryTable({ vat }: { vat: VATSummary }) {
  return (
    <Card withBorder>
      <Title order={4} mb="sm">VAT Summary</Title>
      <Table striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>VAT Rate</Table.Th>
            <Table.Th>Total (ex VAT)</Table.Th>
            <Table.Th>Total VAT</Table.Th>
            <Table.Th>Invoices</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {vat.items.map((row) => (
            <Table.Tr key={row.vat_rate}>
              <Table.Td>{row.vat_rate}%</Table.Td>
              <Table.Td>&euro;{row.total_excl}</Table.Td>
              <Table.Td>&euro;{row.total_vat}</Table.Td>
              <Table.Td>{row.invoice_count}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Card>
  )
}
