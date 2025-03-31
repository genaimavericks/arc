import { test, expect } from '@playwright/test';

test('Debug hero page structure', async ({ page }) => {
  console.log('Starting debug test...');
  
  // Navigate to the hero page
  await page.goto('/');
  console.log('Navigated to hero page');
  
  // Take a screenshot
  await page.screenshot({ path: 'test-results/hero-page-debug.png' });
  
  // Wait for page to be fully loaded
  await page.waitForLoadState('networkidle');
  
  // Get all buttons on the page
  const buttons = await page.locator('button').all();
  console.log(`Found ${buttons.length} buttons`);
  
  // Log info about each button
  for (let i = 0; i < buttons.length; i++) {
    const button = buttons[i];
    const text = await button.textContent();
    const isVisible = await button.isVisible();
    console.log(`Button ${i+1}: Text="${text}", Visible=${isVisible}`);
    
    // Try to get attributes
    const attributes = await button.evaluate(el => {
      const attr = {};
      for (let i = 0; i < el.attributes.length; i++) {
        const attribute = el.attributes[i];
        attr[attribute.name] = attribute.value;
      }
      return attr;
    });
    console.log(`Button ${i+1} attributes:`, JSON.stringify(attributes));
  }
  
  // Get all links on the page
  const links = await page.locator('a').all();
  console.log(`Found ${links.length} links`);
  
  // Log info about each link
  for (let i = 0; i < links.length; i++) {
    const link = links[i];
    const text = await link.textContent();
    const href = await link.getAttribute('href');
    const isVisible = await link.isVisible();
    console.log(`Link ${i+1}: Text="${text}", href="${href}", Visible=${isVisible}`);
  }
  
  // Also look for specific text elements
  const loginTexts = await page.locator(':text("login")', { exact: false }).all();
  console.log(`Found ${loginTexts.length} elements containing 'login' text`);
  
  const signInTexts = await page.locator(':text("sign in")', { exact: false }).all();
  console.log(`Found ${signInTexts.length} elements containing 'sign in' text`);
  
  // Get HTML structure of sections likely to contain login
  const headerHtml = await page.locator('header').innerHTML();
  console.log('Header HTML:', headerHtml);
  
  const navHtml = await page.locator('nav').innerHTML();
  console.log('Nav HTML:', navHtml);
});
