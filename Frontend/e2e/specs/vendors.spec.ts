import { test, expect } from '@playwright/test'
import { api } from '../helpers/api.ts'

test.describe('Vendors', () => {
  test('list page renders vendor table', async ({ page }) => {
    await page.goto('/vendors')

    await expect(page.getByRole('heading', { name: 'Vendors' })).toBeVisible()
    await expect(page.getByText('Add Vendor')).toBeVisible()
  })

  test('create and delete vendor flow', async ({ page }) => {
    const vendorName = `E2E Test Vendor ${Date.now()}`

    // Navigate to new vendor form
    await page.goto('/vendors/new')
    await expect(page.getByRole('heading', { name: 'New Vendor' })).toBeVisible()

    // Fill in the form
    await page.getByRole('textbox', { name: 'Name' }).fill(vendorName)
    await page.getByRole('button', { name: 'Create' }).click()

    // Should navigate back to list
    await expect(page).toHaveURL(/\/vendors$/)
    await expect(page.getByText(vendorName)).toBeVisible()

    // Cleanup via API
    const { items } = await api.listVendors()
    const created = items.find((v) => v.name === vendorName)
    if (created) await api.deleteVendor(created.id)
  })

  test('clicking a vendor navigates to detail', async ({ page }) => {
    await page.goto('/vendors')

    const firstRow = page.locator('table tbody tr').first()
    await firstRow.waitFor()
    await firstRow.click()

    await expect(page).toHaveURL(/\/vendors\/.+/)
    await expect(page.getByText('Back')).toBeVisible()
    await expect(page.getByText('Invoice History')).toBeVisible()
  })
})
