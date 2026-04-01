import {
  Card,
  Title,
  Group,
  Alert,
  Table,
  Badge,
  ScrollArea,
} from '@mantine/core'
import { IconAlertCircle, IconAlertTriangle } from '@tabler/icons-react'
import type { MissingInvoiceAlertList } from '../../../api/types/index.ts'

export function MissingInvoiceAlerts({ alerts, navigate }: {
  alerts?: MissingInvoiceAlertList
  navigate: (path: string) => void
}) {
  return (
    <>
      {alerts && alerts.items.length > 0 && (
        <Card withBorder>
          <Group mb="sm">
            <IconAlertTriangle size={20} color="var(--mantine-color-orange-6)" />
            <Title order={4}>Missing Invoice Alerts</Title>
          </Group>
          <ScrollArea>
          <Table striped highlightOnHover miw={400}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Vendor</Table.Th>
                <Table.Th>Billing Cycle</Table.Th>
                <Table.Th>Last Invoice</Table.Th>
                <Table.Th>Expected</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {alerts.items.map((a) => (
                <Table.Tr
                  key={`${a.vendor_id}-${a.expected_period}`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/vendors/${a.vendor_id}`)}
                >
                  <Table.Td fw={500}>{a.vendor_name}</Table.Td>
                  <Table.Td><Badge color="blue">{a.billing_cycle}</Badge></Table.Td>
                  <Table.Td>{a.last_invoice_period ?? 'never'}</Table.Td>
                  <Table.Td><Badge color="orange">{a.expected_period}</Badge></Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          </ScrollArea>
        </Card>
      )}

      {alerts && alerts.items.length === 0 && (
        <Alert icon={<IconAlertCircle size={16} />} color="green">
          No missing invoices detected.
        </Alert>
      )}
    </>
  )
}
