import { useState } from 'react';
import { Title, Stack, Group, Grid } from '@mantine/core';
import { useNavigate } from 'react-router-dom';
import { useMissingInvoiceAlertsQuery } from '../../store/dashboardApi.ts';
import { KpiCards } from './_components/KpiCards.tsx';
import { SpendCharts } from './_components/SpendCharts.tsx';
import { VatSummaryTable } from './_components/VatSummaryTable.tsx';
import { MissingInvoiceAlerts } from './_components/MissingInvoiceAlerts.tsx';
import { PeriodPicker, resolvePeriods } from './_components/PeriodPicker.tsx';
import { DashboardSkeleton } from './_components/DashboardSkeleton.tsx';
import { CategoryDetailModal } from './_components/CategoryDetailModal.tsx';
import { TaxSummaryCard } from './_components/TaxSummaryCard.tsx';
import { useDashboardData } from './useDashboardData.ts';

export function DashboardPage() {
  const navigate = useNavigate();
  const [preset, setPreset] = useState('this_month');
  const [customMonth, setCustomMonth] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const periods = resolvePeriods(preset, customMonth);
  const { summary, byCategory, byVendor, vat, mom, tax, earnings, withholdings, isLoading } =
    useDashboardData(periods);
  const { data: alerts } = useMissingInvoiceAlertsQuery();

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Dashboard</Title>
        <PeriodPicker
          preset={preset}
          onPresetChange={setPreset}
          customMonth={customMonth}
          onCustomMonthChange={setCustomMonth}
        />
      </Group>

      {isLoading ? (
        <DashboardSkeleton />
      ) : (
        <>
          {summary && (
            <KpiCards summary={summary} tax={tax} earnings={earnings} withholdings={withholdings} />
          )}

          <SpendCharts
            byCategory={byCategory}
            byVendor={byVendor}
            mom={mom}
            onCategoryClick={setSelectedCategory}
          />

          <Grid>
            <Grid.Col span={{ base: 12, md: 4 }}>
              {vat && vat.items.length > 0 && <VatSummaryTable vat={vat} />}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 4 }}>
              <TaxSummaryCard tax={tax} onCategoryClick={setSelectedCategory} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 4 }}>
              <MissingInvoiceAlerts alerts={alerts} navigate={navigate} />
            </Grid.Col>
          </Grid>
        </>
      )}

      <CategoryDetailModal
        category={selectedCategory}
        periods={periods}
        opened={selectedCategory !== null}
        onClose={() => setSelectedCategory(null)}
      />
    </Stack>
  );
}
