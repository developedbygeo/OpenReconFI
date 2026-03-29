import {
  Title,
  Table,
  Badge,
  Group,
  Button,
  Alert,
  Text,
} from '@mantine/core'
import { IconPlus, IconAlertCircle } from '@tabler/icons-react'
import { useNavigate } from 'react-router-dom'
import { useListVendorsQuery } from '../../../store/vendorsApi.ts'
import { VendorListSkeleton } from './VendorListSkeleton.tsx'

const CYCLE_COLORS: Record<string, string> = {
  monthly: 'blue',
  bimonthly: 'cyan',
  quarterly: 'teal',
  annual: 'grape',
  irregular: 'gray',
}

export function VendorListPage() {
  const navigate = useNavigate()
  const { data, isLoading, error } = useListVendorsQuery({ limit: 100 })

  if (isLoading) return <VendorListSkeleton />

  if (error) {
    return (
      <Alert icon={<IconAlertCircle size={16} />} color="red" title="Error">
        Failed to load vendors.
      </Alert>
    )
  }

  const vendors = data?.items ?? []

  return (
    <>
      <Group justify="space-between" mb="md">
        <Title order={2}>Vendors</Title>
        <Button
          leftSection={<IconPlus size={16} />}
          onClick={() => navigate('/vendors/new')}
        >
          Add Vendor
        </Button>
      </Group>

      {vendors.length === 0 ? (
        <Text c="dimmed">No vendors yet.</Text>
      ) : (
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>VAT Rate</Table.Th>
              <Table.Th>Billing Cycle</Table.Th>
              <Table.Th>Aliases</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {vendors.map((v) => (
              <Table.Tr
                key={v.id}
                style={{ cursor: 'pointer' }}
                onClick={() => navigate(`/vendors/${v.id}`)}
              >
                <Table.Td fw={500}>{v.name}</Table.Td>
                <Table.Td>{v.default_category ?? '—'}</Table.Td>
                <Table.Td>{v.default_vat_rate ? `${v.default_vat_rate}%` : '—'}</Table.Td>
                <Table.Td>
                  <Badge color={CYCLE_COLORS[v.billing_cycle] ?? 'gray'}>
                    {v.billing_cycle}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  {v.aliases?.length ? v.aliases.join(', ') : '—'}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </>
  )
}
