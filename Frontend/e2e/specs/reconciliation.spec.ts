import { test, expect } from '@playwright/test'

test.describe('Reconciliation', () => {
  test('statement upload page renders dropzone', async ({ page }) => {
    await page.goto('/reconciliation')

    await expect(page.getByRole('heading', { name: 'Upload Bank Statement' })).toBeVisible()
    await expect(page.getByText(/Supported formats/)).toBeVisible()
    await expect(page.getByText(/Drag a statement file/)).toBeVisible()
  })

  test('match review page renders', async ({ page }) => {
    await page.goto('/reconciliation/matches')

    await expect(page.getByRole('heading', { name: 'Match Review' })).toBeVisible()
    await expect(page.getByText('Run Matching')).toBeVisible()
  })

  test('manual match page renders', async ({ page }) => {
    await page.goto('/reconciliation/manual-match')

    await expect(page.getByRole('heading', { name: 'Manual Matching' })).toBeVisible()
    await expect(page.getByText('Create Match')).toBeVisible()
  })

  test('reconciliation overview page renders', async ({ page }) => {
    await page.goto('/reconciliation/overview')

    await expect(page.getByRole('heading', { name: 'Reconciliation Overview' })).toBeVisible()
  })
})
