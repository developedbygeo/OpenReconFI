import { SegmentedControl, Select, Group } from '@mantine/core';
import { MonthPickerInput } from '@mantine/dates';
import '@mantine/dates/styles.css';

function toYYYYMM(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function monthsAgo(n: number): Date {
  const d = new Date();
  d.setDate(1);
  d.setMonth(d.getMonth() - n);
  return d;
}

function monthRange(from: Date, to: Date): string[] {
  const periods: string[] = [];
  const cursor = new Date(from);
  cursor.setDate(1);
  while (cursor <= to) {
    periods.push(toYYYYMM(cursor));
    cursor.setMonth(cursor.getMonth() + 1);
  }
  return periods;
}

const PRESETS = [
  { label: 'This month', value: 'this_month' },
  { label: 'Last month', value: 'last_month' },
  { label: 'Last 3m', value: 'last_3' },
  { label: 'Last 6m', value: 'last_6' },
  { label: 'YTD', value: 'ytd' },
  { label: 'All time', value: 'all_time' },
  { label: 'Custom', value: 'custom' },
];

// eslint-disable-next-line react-refresh/only-export-components
export function resolvePeriods(preset: string, customMonth: string | null): string[] {
  const now = new Date();
  switch (preset) {
    case 'this_month':
      return [toYYYYMM(now)];
    case 'last_month':
      return [toYYYYMM(monthsAgo(1))];
    case 'last_3':
      return monthRange(monthsAgo(2), now);
    case 'last_6':
      return monthRange(monthsAgo(5), now);
    case 'ytd': {
      const jan = new Date(now.getFullYear(), 0, 1);
      return monthRange(jan, now);
    }
    case 'all_time':
      return [];
    case 'custom':
      return customMonth ? [toYYYYMM(new Date(customMonth))] : [toYYYYMM(now)];
    default:
      return [toYYYYMM(now)];
  }
}

export function PeriodPicker({
  preset,
  onPresetChange,
  customMonth,
  onCustomMonthChange,
}: {
  preset: string;
  onPresetChange: (v: string) => void;
  customMonth: string | null;
  onCustomMonthChange: (v: string | null) => void;
}) {
  return (
    <Group gap="sm" wrap="wrap">
      <SegmentedControl size="xs" data={PRESETS} value={preset} onChange={onPresetChange} visibleFrom="sm" />
      <Select
        size="xs"
        data={PRESETS}
        value={preset}
        onChange={(v) => onPresetChange(v ?? 'this_month')}
        hiddenFrom="sm"
        style={{ flex: '1 1 140px' }}
      />
      {preset === 'custom' && (
        <MonthPickerInput
          placeholder="Pick month"
          value={customMonth}
          onChange={onCustomMonthChange}
          size="xs"
          style={{ minWidth: 140 }}
        />
      )}
    </Group>
  );
}
