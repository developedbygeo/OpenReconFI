import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test('renders dashboard with KPI cards', async ({ page }) => {
    await page.goto('/dashboard')

    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
    await expect(page.getByText('Tax & Non-Invoice Costs')).toBeVisible()
    await expect(page.getByText('Missing Invoice Alerts')).toBeVisible()
  })

  test('/ redirects to /dashboard', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/dashboard/)
  })
})
