import { test, expect } from '@playwright/test';

test('Debug login form fields', async ({ page }) => {
  console.log('Starting login form debug...');
  
  // Navigate to the hero page
  await page.goto('/');
  console.log('Navigated to hero page');
  
  // Click on the "Sign In" link
  await Promise.all([
    page.waitForNavigation(),
    page.click('a[href="/login"]')
  ]);
  console.log('Clicked Sign In, now on login page');
  
  // Take a screenshot
  await page.screenshot({ path: 'test-results/login-page-debug.png' });
  
  // Get all input fields on the page
  const inputs = await page.locator('input').all();
  console.log(`Found ${inputs.length} input fields`);
  
  // Analyze each input
  for (let i = 0; i < inputs.length; i++) {
    const input = inputs[i];
    const type = await input.getAttribute('type') || 'none';
    const name = await input.getAttribute('name') || 'none';
    const id = await input.getAttribute('id') || 'none';
    const placeholder = await input.getAttribute('placeholder') || 'none';
    const isVisible = await input.isVisible();
    
    console.log(`Input ${i+1}: Type=${type}, Name=${name}, ID=${id}, Placeholder=${placeholder}, Visible=${isVisible}`);
  }
  
  // Get all buttons
  const buttons = await page.locator('button').all();
  console.log(`Found ${buttons.length} buttons`);
  
  // Analyze each button
  for (let i = 0; i < buttons.length; i++) {
    const button = buttons[i];
    const text = await button.textContent();
    const type = await button.getAttribute('type') || 'none';
    const isVisible = await button.isVisible();
    
    console.log(`Button ${i+1}: Text="${text}", Type=${type}, Visible=${isVisible}`);
  }
  
  // Try to interact with form
  console.log('Trying to interact with email/username field...');
  try {
    const emailField = await page.waitForSelector('input[type="email"], input[name="email"], input[name="username"], input[id="email"], input[id="username"]', { timeout: 5000 });
    console.log('Found email/username field, trying to fill it');
    await emailField.fill('admin');
    console.log('Successfully filled email field');
  } catch (e) {
    console.error('Failed to find or fill email field:', e);
  }
  
  console.log('Trying to interact with password field...');
  try {
    const passwordField = await page.waitForSelector('input[type="password"], input[name="password"], input[id="password"]', { timeout: 5000 });
    console.log('Found password field, trying to fill it');
    await passwordField.fill('admin123');
    console.log('Successfully filled password field');
  } catch (e) {
    console.error('Failed to find or fill password field:', e);
  }
  
  // Try to identify the submit button
  console.log('Trying to identify submit button...');
  try {
    const submitButton = await page.waitForSelector('button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Sign in"), button:has-text("Log in")', { timeout: 5000 });
    console.log('Found submit button, details:');
    const buttonText = await submitButton.textContent();
    const buttonType = await submitButton.getAttribute('type');
    console.log(`Button text: "${buttonText}", type: ${buttonType}`);
  } catch (e) {
    console.error('Failed to find submit button:', e);
  }
});
