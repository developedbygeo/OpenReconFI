import { useEffect } from 'react'
import {
  Title,
  Stack,
  TextInput,
  Select,
  Button,
  Group,
  TagsInput,
  NumberInput,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { notifications } from '@mantine/notifications'
import { IconArrowLeft } from '@tabler/icons-react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  useGetVendorQuery,
  useCreateVendorMutation,
  useUpdateVendorMutation,
} from '../../../store/vendorsApi.ts'
import type { BillingCycle } from '../../../api/types/index.ts'

const BILLING_CYCLES = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'bimonthly', label: 'Bimonthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'annual', label: 'Annual' },
  { value: 'irregular', label: 'Irregular' },
]

export function VendorFormPage() {
  const { id } = useParams<{ id: string }>()
  const isEdit = id !== undefined && id !== 'new'
  const navigate = useNavigate()

  const { data: existingVendor } = useGetVendorQuery(id!, { skip: !isEdit })
  const [createVendor, { isLoading: creating }] = useCreateVendorMutation()
  const [updateVendor, { isLoading: updating }] = useUpdateVendorMutation()

  const form = useForm({
    initialValues: {
      name: '',
      aliases: [] as string[],
      default_category: '',
      default_vat_rate: '' as string | number,
      billing_cycle: 'monthly' as string,
    },
    validate: {
      name: (v) => (v.trim() ? null : 'Name is required'),
    },
  })

  useEffect(() => {
    if (existingVendor) {
      form.setValues({
        name: existingVendor.name,
        aliases: existingVendor.aliases ?? [],
        default_category: existingVendor.default_category ?? '',
        default_vat_rate: existingVendor.default_vat_rate ?? '',
        billing_cycle: existingVendor.billing_cycle,
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [existingVendor])

  const handleSubmit = async (values: typeof form.values) => {
    const payload = {
      name: values.name,
      aliases: values.aliases.length > 0 ? values.aliases : null,
      default_category: values.default_category || null,
      default_vat_rate: values.default_vat_rate !== '' ? Number(values.default_vat_rate) : null,
      billing_cycle: values.billing_cycle as BillingCycle,
    }

    try {
      if (isEdit) {
        await updateVendor({ vendorId: id!, body: payload }).unwrap()
        notifications.show({ title: 'Updated', message: `${values.name} updated.`, color: 'green' })
      } else {
        await createVendor(payload).unwrap()
        notifications.show({ title: 'Created', message: `${values.name} created.`, color: 'green' })
      }
      navigate('/vendors')
    } catch {
      notifications.show({ title: 'Error', message: 'Could not save vendor.', color: 'red' })
    }
  }

  return (
    <Stack>
      <Group>
        <Button
          variant="subtle"
          leftSection={<IconArrowLeft size={16} />}
          onClick={() => navigate('/vendors')}
        >
          Back
        </Button>
      </Group>

      <Title order={2}>{isEdit ? 'Edit Vendor' : 'New Vendor'}</Title>

      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack>
          <TextInput
            label="Name"
            required
            {...form.getInputProps('name')}
          />
          <TagsInput
            label="Aliases"
            description="Bank description variants — press Enter to add"
            {...form.getInputProps('aliases')}
          />
          <TextInput
            label="Default Category"
            {...form.getInputProps('default_category')}
          />
          <NumberInput
            label="Default VAT Rate (%)"
            min={0}
            max={100}
            decimalScale={2}
            {...form.getInputProps('default_vat_rate')}
          />
          <Select
            label="Billing Cycle"
            data={BILLING_CYCLES}
            {...form.getInputProps('billing_cycle')}
          />
          <Button type="submit" loading={creating || updating} w="fit-content">
            {isEdit ? 'Update' : 'Create'}
          </Button>
        </Stack>
      </form>
    </Stack>
  )
}
