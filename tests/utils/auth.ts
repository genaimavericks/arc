import { Page } from '@playwright/test';
import { users } from './data/testData';

/**
 * Utility functions for authentication in automation tests
 */
export async function login(page: Page, username?: string, password?: string) {
  // Use provided credentials or fall back to admin credentials from testData
  const user = username || users.admin.username;
  const pass = password || users.admin.password;
  
  console.log('Starting login process...');
  
  // Navigate to the hero/landing page first
  await page.goto('/');
  console.log('Navigated to hero page');
  
  // Wait for hero page to be fully loaded
  await page.waitForLoadState('networkidle');
  
  // Click on the "Sign In" link
  console.log('Clicking Sign In link');
  await Promise.all([
    page.waitForNavigation({ timeout: 10000 }),
    page.click('a[href="/login"]')
  ]);
  console.log('Navigated to login page');
  
  // Fill in login form using correct selectors as found in debug test
  await page.waitForSelector('#username');
  await page.fill('#username', user);
  await page.fill('#password', pass);
  console.log('Filled login form');
  
  // Click login button and wait for navigation
  await Promise.all([
    page.waitForNavigation(),
    page.click('button[type="submit"]')
  ]);
  console.log('Submitted login form');
}

export async function logout(page: Page) {
  // Flexible selector to find user menu in different UI implementations
  const userMenuSelectors = [
    '[aria-label="User menu"]',
    '.user-menu',
    '.avatar',
    '.user-dropdown'
  ];
  
  // Find the right selector
  for (const selector of userMenuSelectors) {
    const menuButton = page.locator(selector);
    if (await menuButton.isVisible()) {
      // Click user menu
      await menuButton.click();
      break;
    }
  }
  
  // Try different logout text options
  const logoutSelectors = [
    'text=Logout',
    'text=Log out',
    'text=Sign out',
    '[data-testid="logout"]'
  ];
  
  // Find and click the right logout button
  for (const selector of logoutSelectors) {
    const logoutButton = page.locator(selector);
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
      break;
    }
  }
  
  // Wait for redirect to landing/hero page
  await page.waitForURL('/');
}
