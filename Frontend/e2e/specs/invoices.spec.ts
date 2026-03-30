import { test, expect } from '@playwright/test'

test.describe('Invoices', () => {
  test('list page renders table', async ({ page }) => {
    await page.goto('/invoices')

    await expect(page.getByRole('heading', { name: 'Invoices' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Vendor' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Amount (incl.)' })).toBeVisible()
  })

  test('filter dropdowns are present', async ({ page }) => {
    await page.goto('/invoices')

    await expect(page.getByPlaceholder('Filter by status')).toBeVisible()
    await expect(page.getByPlaceholder('Filter by category')).toBeVisible()
  })

  test('clicking an invoice navigates to detail', async ({ page }) => {
    await page.goto('/invoices')

    // Wait for table to load, then click first row
    const firstRow = page.locator('table tbody tr').first()
    await firstRow.waitFor()
    await firstRow.click()

    await expect(page).toHaveURL(/\/invoices\/.+/)
    await expect(page.getByText('Back')).toBeVisible()
  })
})
