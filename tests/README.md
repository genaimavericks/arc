# RSW Web GUI Automation

This directory contains automated tests for the RSW web application using Playwright.

## Overview

The automation framework is structured as follows:

```
tests/
├── auth/              # Authentication-related tests
├── dashboard/         # Dashboard functionality tests
└── utils/             # Helper utilities and functions
```

## Running Tests

You can run tests using the following npm scripts:

- `npm test` - Run all tests in headless mode
- `npm run test:ui` - Run tests with Playwright UI
- `npm run test:debug` - Run tests in debug mode
- `npm run test:report` - View HTML test report from previous runs

## Writing Tests

### Naming Convention

Test files should follow the naming pattern: `feature.spec.ts`

### Test Structure

Each test file should:
1. Import the necessary Playwright test utilities
2. Group related tests using `test.describe()`
3. Use helper functions from the utils directory for common operations
4. Follow the pattern: setup → action → assertion

Example:

```typescript
import { test, expect } from '@playwright/test';
import { login } from '../utils/auth';

test.describe('Feature Name', () => {
  test('should perform expected action', async ({ page }) => {
    // Setup
    await page.goto('/page-url');
    
    // Action
    await page.click('button');
    
    // Assertion
    await expect(page.locator('.result')).toBeVisible();
  });
});
```

## Selectors Strategy

When selecting elements, use the following priority:

1. `data-testid` attributes (preferred for testing)
2. Accessible roles or labels
3. CSS selectors (as a last resort)

Example:
```typescript
// Best: Test ID
await page.click('[data-testid="submit-button"]');

// Good: Accessible label
await page.click('button[aria-label="Submit"]');

// Last resort: Text content
await page.click('text=Submit');
```

## CI/CD Integration

This automation framework is configured to work with CI/CD systems. In CI environments, tests will:
- Run with 2 retries on failure
- Use a single worker to avoid resource contention
- Generate HTML reports for review

## Next Steps
To complete your web GUI automation setup:

Test Environment Configuration:
Create a .env.test file with specific test environment variables
Adjust your backend startup parameters for testing
Mock Data Generation:
Add more test data generators as needed for specific test scenarios
Test Database Setup:
Implement database seed/reset utilities between test runs