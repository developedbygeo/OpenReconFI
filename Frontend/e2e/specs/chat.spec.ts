import { test, expect } from '@playwright/test'

test.describe('Chat', () => {
  test('renders chat page with input', async ({ page }) => {
    await page.goto('/chat')

    await expect(page.getByRole('heading', { name: 'Expense Chat' })).toBeVisible()
    await expect(page.getByText('Clear')).toBeVisible()
  })

  test('can type and send a message', async ({ page }) => {
    await page.goto('/chat')

    const input = page.getByPlaceholder(/ask/i)
    await input.waitFor()
    await input.fill('What are my top vendors?')
    await input.press('Enter')

    // Wait for streaming response to appear
    await expect(page.locator('text=OpenReconFi').last()).toBeVisible({ timeout: 15_000 })
  })
})
