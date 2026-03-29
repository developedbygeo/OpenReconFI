import {
  Card,
  Title,
  Text,
  Grid,
  Group,
  Progress,
  Stack,
  ColorSwatch,
  Paper,
  useMantineTheme,
} from '@mantine/core'
import { DonutChart, AreaChart } from '@mantine/charts'
import '@mantine/charts/styles.css'
import type { CategorySpendList, CategorySpend, VendorSpendList, MoMComparison } from '../../../api/types/index.ts'

const CATEGORY_COLORS = ['blue', 'cyan', 'teal', 'violet', 'grape', 'orange', 'pink', 'lime']
const VENDOR_COLORS = ['violet', 'blue', 'teal', 'orange', 'grape', 'cyan', 'pink', 'lime']

function CategoryTooltip({ item }: { item: CategorySpend }) {
  return (
    <Paper p="xs" withBorder shadow="sm">
      <Text size="sm" fw={600} mb={4}>{item.category}</Text>
      <Stack gap={2}>
        <Group justify="space-between" gap="lg">
          <Text size="xs" c="dimmed">Excl. VAT</Text>
          <Text size="xs" fw={500}>&euro;{item.total_excl}</Text>
        </Group>
        <Group justify="space-between" gap="lg">
          <Text size="xs" c="dimmed">VAT</Text>
          <Text size="xs" fw={500}>&euro;{item.total_vat}</Text>
        </Group>
        <Group justify="space-between" gap="lg">
          <Text size="xs" c="dimmed">Incl. VAT</Text>
          <Text size="xs" fw={500}>&euro;{item.total_incl}</Text>
        </Group>
        <Group justify="space-between" gap="lg">
          <Text size="xs" c="dimmed">Invoices</Text>
          <Text size="xs" fw={500}>{item.invoice_count}</Text>
        </Group>
      </Stack>
    </Paper>
  )
}

export function SpendCharts({ byCategory, byVendor, mom, onCategoryClick }: {
  byCategory?: CategorySpendList
  byVendor?: VendorSpendList
  mom?: MoMComparison
  onCategoryClick?: (category: string) => void
}) {
  const theme = useMantineTheme()
  const categoryItems = byCategory?.items ?? []
  const vendorItems = byVendor?.items ?? []
  const maxVendorSpend = vendorItems.length > 0
    ? Math.max(...vendorItems.map((v) => parseFloat(v.total_incl)))
    : 1

  const categoryMap = new Map(categoryItems.map((c) => [c.category, c]))

  return (
    <>
      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder h="100%">
            <Title order={4} mb="sm">Spend by Category</Title>
            {categoryItems.length > 0 ? (
              <>
                <DonutChart
                  h={200}
                  data={categoryItems.map((c, i) => ({
                    name: c.category,
                    value: parseFloat(c.total_incl),
                    color: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
                  }))}
                  tooltipDataSource="segment"
                  chartLabel={`€${categoryItems.reduce((s, c) => s + parseFloat(c.total_incl), 0).toFixed(0)}`}
                  tooltipProps={{
                    content: ({ payload }) => {
                      const name = payload?.[0]?.name as string | undefined
                      const item = name ? categoryMap.get(name) : undefined
                      if (!item) return null
                      return <CategoryTooltip item={item} />
                    },
                  }}
                  pieProps={{
                    onClick: (_: unknown, index: number) => {
                      const item = categoryItems[index]
                      if (item && onCategoryClick) onCategoryClick(item.category)
                    },
                    style: { cursor: 'pointer' },
                  }}
                />
                <Group gap="sm" mt="md" justify="center" wrap="wrap">
                  {categoryItems.map((c, i) => (
                    <Group
                      key={c.category}
                      gap={6}
                      style={{ cursor: 'pointer' }}
                      onClick={() => onCategoryClick?.(c.category)}
                    >
                      <ColorSwatch
                        color={theme.colors[CATEGORY_COLORS[i % CATEGORY_COLORS.length]][6]}
                        size={12}
                      />
                      <Text size="xs">{c.category}</Text>
                    </Group>
                  ))}
                </Group>
              </>
            ) : (
              <Text c="dimmed" size="sm">No category data.</Text>
            )}
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder h="100%">
            <Title order={4} mb="sm">Spend by Vendor</Title>
            {vendorItems.length > 0 ? (
              <Stack gap="sm">
                {vendorItems
                  .slice()
                  .sort((a, b) => parseFloat(b.total_incl) - parseFloat(a.total_incl))
                  .map((v, i) => {
                    const amount = parseFloat(v.total_incl)
                    return (
                      <div key={v.vendor}>
                        <Group justify="space-between" mb={4}>
                          <Text size="sm" fw={500} truncate maw="60%">{v.vendor}</Text>
                          <Text size="sm" c="dimmed">&euro;{v.total_incl}</Text>
                        </Group>
                        <Progress
                          value={(amount / maxVendorSpend) * 100}
                          color={VENDOR_COLORS[i % VENDOR_COLORS.length]}
                          size="md"
                          radius="xl"
                        />
                      </div>
                    )
                  })}
              </Stack>
            ) : (
              <Text c="dimmed" size="sm">No vendor data.</Text>
            )}
          </Card>
        </Grid.Col>
      </Grid>

      {mom && mom.items.length > 0 && (
        <Card withBorder>
          <Title order={4} mb="sm">Month-over-Month Trend</Title>
          <AreaChart
            h={240}
            data={mom.items.map((m) => ({
              period: m.period,
              'Spend (incl.)': parseFloat(m.total_incl),
              'Spend (excl.)': parseFloat(m.total_excl),
            }))}
            dataKey="period"
            series={[
              { name: 'Spend (incl.)', color: 'teal' },
              { name: 'Spend (excl.)', color: 'cyan' },
            ]}
            curveType="monotone"
            withDots
          />
        </Card>
      )}
    </>
  )
}
