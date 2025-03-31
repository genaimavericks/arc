import { Page } from '@playwright/test';

/**
 * Base Page Object class with common functionality across all pages
 */
export class BasePage {
  protected page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * Wait for page load to complete
   */
  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Click an element and wait for navigation
   */
  async clickAndWaitForNavigation(selector: string) {
    await Promise.all([
      this.page.waitForNavigation(),
      this.page.click(selector)
    ]);
  }

  /**
   * Check if an element exists on the page
   */
  async elementExists(selector: string): Promise<boolean> {
    return (await this.page.$(selector)) !== null;
  }

  /**
   * Fill a form field
   */
  async fillField(selector: string, value: string) {
    await this.page.fill(selector, value);
  }

  /**
   * Get text from an element
   */
  async getText(selector: string): Promise<string> {
    return await this.page.locator(selector).innerText();
  }
}
