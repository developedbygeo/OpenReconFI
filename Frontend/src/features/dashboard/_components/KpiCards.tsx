import {
  SimpleGrid,
  Card,
  Text,
} from '@mantine/core'
import type { SpendSummary, TaxSummary, EarningsSummary, WithholdingsSummary } from '../../../api/types/index.ts'

export function KpiCards({ summary, tax, earnings, withholdings }: {
  summary: SpendSummary
  tax?: TaxSummary
  earnings?: EarningsSummary
  withholdings?: WithholdingsSummary
}) {
  return (
    <SimpleGrid cols={{ base: 2, sm: 3, lg: 7 }}>
      <Card withBorder>
        <Text size="xs" c="dimmed" tt="uppercase">Earnings</Text>
        <Text size="xl" fw={700} c="green">
          {earnings ? `€${Number(earnings.total_earnings).toFixed(2)}` : '—'}
        </Text>
        {earnings && earnings.transaction_count > 0 && (
          <Text size="xs" c="dimmed">{earnings.transaction_count} payment{earnings.transaction_count !== 1 ? 's' : ''}</Text>
        )}
      </Card>
      <Card withBorder>
        <Text size="xs" c="dimmed" tt="uppercase">Total Spend (ex VAT)</Text>
        <Text size="xl" fw={700}>&euro;{summary.total_spend_excl}</Text>
      </Card>
      <Card withBorder>
        <Text size="xs" c="dimmed" tt="uppercase">Total VAT</Text>
        <Text size="xl" fw={700}>&euro;{summary.total_vat}</Text>
      </Card>
      <Card withBorder>
        <Text size="xs" c="dimmed" tt="uppercase">Taxes &amp; Fees</Text>
        <Text size="xl" fw={700} c={tax && Number(tax.total_amount) < 0 ? 'red' : undefined}>
          {tax ? `€${Math.abs(Number(tax.total_amount)).toFixed(2)}` : '—'}
        </Text>
        {tax && tax.transaction_count > 0 && (
          <Text size="xs" c="dimmed">{tax.transaction_count} transaction{tax.transaction_count !== 1 ? 's' : ''}</Text>
        )}
      </Card>
      <Card withBorder>
        <Text size="xs" c="dimmed" tt="uppercase">Owner Withdrawals</Text>
        <Text size="xl" fw={700} c="orange">
          {withholdings && withholdings.total_amount != null
            ? `€${Math.abs(Number(withholdings.total_amount) || 0).toFixed(2)}`
            : '—'}
        </Text>
        {withholdings && withholdings.transaction_count > 0 && (
          <Text size="xs" c="dimmed">{withholdings.transaction_count} withdrawal{withholdings.transaction_count !== 1 ? 's' : ''}</Text>
        )}
      </Card>
      <Card withBorder>
        <Text size="xs" c="dimmed" tt="uppercase">Invoices</Text>
        <Text size="xl" fw={700}>{summary.invoice_count}</Text>
      </Card>
      <Card withBorder>
        <Text size="xs" c="dimmed" tt="uppercase">Match Rate</Text>
        <Text size="xl" fw={700}>
          {summary.invoice_count > 0
            ? `${Math.round((summary.matched_count / summary.invoice_count) * 100)}%`
            : '—'}
        </Text>
      </Card>
    </SimpleGrid>
  )
}
