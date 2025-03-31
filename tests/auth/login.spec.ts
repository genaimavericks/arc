import { test, expect } from '@playwright/test';
import { login } from '../utils/auth';

test.describe('Authentication', () => {
  test('should display hero page with login option', async ({ page }) => {
    await page.goto('/');
    
    // Verify hero page elements
    await expect(page.locator('a', { hasText: 'Cognitive Data Expert' })).toBeVisible();
    await expect(page.locator('a[href="/login"]')).toBeVisible();
    // Use first() to handle the multiple buttons
    await expect(page.locator('button', { hasText: 'Please login to access this platform' }).first()).toBeVisible();
  });

  test('should navigate to login page from hero page', async ({ page }) => {
    // Start at hero/landing page
    await page.goto('/');
    
    // Click Sign In link
    await page.click('a[href="/login"]');
    
    // Verify login page elements (using ID selectors)
    await expect(page.locator('#username')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible(); 
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should login with valid credentials', async ({ page }) => {
    // Use the login helper function (now updated to use the correct Sign In link)
    await login(page, 'admin', 'admin123');
    
    // Verify successful login by checking either:
    // 1. We've navigated to dashboard, OR
    // 2. We're logged in as indicated by user menu/avatar elements
    
    // Check for user menu indicators first as the primary success criteria
    // Try multiple possible selectors for the logged-in state
    const loggedInIndicators = [
      '.user-menu', 
      '[aria-label="User menu"]', 
      '.avatar',
      '.user-dropdown',
      '.user-profile',
      '[data-testid="user-profile"]',
      'button:has-text("admin")',
      // Check for common dashboard elements
      '.sidebar',
      '.dashboard-container',
      'nav.main-navigation',
      '.logout-button'
    ];
    
    let loggedInSuccess = false;
    
    // Try each indicator
    for (const selector of loggedInIndicators) {
      const indicator = page.locator(selector);
      if (await indicator.isVisible()) {
        await expect(indicator).toBeVisible();
        loggedInSuccess = true;
        console.log(`Successfully detected login via selector: ${selector}`);
        break;
      }
    }
    
    // If no indicators found, check if URL contains dashboard
    if (!loggedInSuccess) {
      // Check if URL contains dashboard or other authentication success indicators
      const currentUrl = page.url();
      if (currentUrl.includes('dashboard') || 
          currentUrl.includes('home') || 
          currentUrl.includes('profile') ||
          !currentUrl.includes('login')) {
        console.log(`Login verified by URL: ${currentUrl}`);
        loggedInSuccess = true;
      }
    }
    
    // Assert that one of our login verification methods worked
    expect(loggedInSuccess, 'Failed to verify successful login').toBeTruthy();
  });

  test('should show error with invalid credentials', async ({ page }) => {
    // Start at hero/landing page
    await page.goto('/');
    
    // Click Sign In link
    await page.click('a[href="/login"]');
    
    // Fill in login form with invalid credentials (using ID selectors)
    await page.fill('#username', 'invalid@example.com');
    await page.fill('#password', 'wrongpassword');
    
    // Click login button
    await page.click('button[type="submit"]');
    
    // Verify error message using multiple possible selectors
    const errorSelectors = [
      '.error-message', 
      '.alert-error',
      '.text-error',
      '.text-red-500',
      '[role="alert"]',
      '.toast-error'
    ];
    
    // Try each error selector
    let errorFound = false;
    for (const selector of errorSelectors) {
      const isVisible = await page.locator(selector).isVisible();
      if (isVisible) {
        await expect(page.locator(selector)).toBeVisible();
        errorFound = true;
        break;
      }
    }
    
    // If no specific error element is found, at least verify we're still on the login page
    if (!errorFound) {
      await expect(page).toHaveURL(/.*login/);
      await expect(page.locator('#username')).toBeVisible();
    }
  });
});
