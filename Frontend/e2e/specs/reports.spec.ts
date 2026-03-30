import { test, expect } from '@playwright/test'

test.describe('Reports', () => {
  test('renders reports page with download button', async ({ page }) => {
    await page.goto('/reports')

    await expect(page.getByRole('heading', { name: 'Reports' })).toBeVisible()
    await expect(page.getByText('Download')).toBeVisible()
  })
})
