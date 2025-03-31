import { test, expect } from '@playwright/test';
import { login } from '../utils/auth';

test.describe('Dashboard', () => {
  // Setup: Login before each test
  test.beforeEach(async ({ page }) => {
    // Login now starts from hero page and navigates to login
    await login(page, 'admin', 'admin123');
    // Verify we're on the dashboard
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('should display key dashboard components', async ({ page }) => {
    // Verify dashboard elements
    await expect(page.locator('h1')).toContainText('Dashboard');
    await expect(page.locator('[data-testid="sidebar"]')).toBeVisible();
    await expect(page.locator('[data-testid="user-info"]')).toBeVisible();
  });

  test('should navigate between dashboard sections', async ({ page }) => {
    // Click on the DataPuur section
    await page.click('text=DataPuur');
    await expect(page).toHaveURL(/.*data-puur/);
    
    // Click on the KGInsight section
    await page.click('text=KGInsight');
    await expect(page).toHaveURL(/.*kg-insight/);
  });
});
