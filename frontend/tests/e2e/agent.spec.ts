import { test, expect } from '@playwright/test'

test.describe('ARC / Intel live application', () => {
  test('loads the dashboard and reports provider-aware empty states', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('ARC / INTEL', { exact: true })).toBeVisible()
    await expect(page.getByText('Your market copilot is ready.')).toBeVisible()
    await expect(page.getByText('Connect NewsAPI to populate')).toBeVisible({ timeout: 15_000 })
  })

  test('submits a real chat request and renders the structured response', async ({ page }) => {
    await page.goto('/')
    const input = page.getByPlaceholder('Ask about a market, asset, or event…')
    await input.fill('Analyze Bitcoin current market situation')
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(page.getByText('ARC ANALYST')).toBeVisible({ timeout: 110_000 })
    await expect(page.locator('.messages')).toContainText(/Executive Summary|Analyst unavailable|Market Data/)
  })

  test('supports a follow-up in the same browser conversation', async ({ page }) => {
    await page.goto('/')
    const input = page.getByPlaceholder('Ask about a market, asset, or event…')
    await input.fill('Hello, give a brief educational overview.')
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(page.getByText('ARC ANALYST')).toBeVisible({ timeout: 110_000 })
    await input.fill('What about Ethereum?')
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(page.locator('.messages')).toContainText('What about Ethereum?', { timeout: 110_000 })
    await expect(page.locator('.messages').getByText('ARC ANALYST')).toHaveCount(2, { timeout: 110_000 })
  })
})
