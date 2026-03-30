import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {
  test('sidebar navigates to all top-level pages', async ({ page }) => {
    await page.goto('/dashboard')

    const navItems = [
      { label: 'Invoices', url: '/invoices' },
      { label: 'Collection', url: '/collection' },
      { label: 'Vendors', url: '/vendors' },
      { label: 'Reports', url: '/reports' },
      { label: 'Chat', url: '/chat' },
      { label: 'Dashboard', url: '/dashboard' },
    ]

    for (const { label, url } of navItems) {
      await page.getByText(label, { exact: true }).first().click()
      await expect(page).toHaveURL(new RegExp(url))
    }
  })
})
