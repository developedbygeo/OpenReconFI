import { test, expect } from '@playwright/test'

test.describe('Collection', () => {
  test('renders collection page with sync button', async ({ page }) => {
    await page.goto('/collection')

    await expect(page.getByRole('heading', { name: 'Collection' })).toBeVisible()
    await expect(page.getByText('Sync Gmail')).toBeVisible()
    await expect(page.getByText('Job History')).toBeVisible()
  })
})
