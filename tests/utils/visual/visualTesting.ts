import { Page, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

/**
 * Utilities for visual testing and screenshot comparison
 */
export class VisualTesting {
  /**
   * Take a screenshot of an element and compare with baseline
   * 
   * @param page Playwright page object
   * @param selector CSS or test-id selector for the element
   * @param screenshotName Name of the screenshot (used for file naming)
   * @param updateBaseline Whether to update the baseline image
   */
  static async compareElementScreenshot(
    page: Page,
    selector: string,
    screenshotName: string,
    updateBaseline: boolean = false
  ) {
    // Create directories if they don't exist
    const screenshotsDir = path.resolve('./test-results/screenshots');
    const baselineDir = path.join(screenshotsDir, 'baseline');
    const actualDir = path.join(screenshotsDir, 'actual');
    const diffDir = path.join(screenshotsDir, 'diff');
    
    [screenshotsDir, baselineDir, actualDir, diffDir].forEach(dir => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    });
    
    // File paths
    const baselinePath = path.join(baselineDir, `${screenshotName}.png`);
    const actualPath = path.join(actualDir, `${screenshotName}.png`);
    
    // Take screenshot of the element
    const element = page.locator(selector);
    await element.screenshot({ path: actualPath });
    
    // If updating baseline or baseline doesn't exist, copy actual to baseline
    if (updateBaseline || !fs.existsSync(baselinePath)) {
      fs.copyFileSync(actualPath, baselinePath);
      return;
    }
    
    // Compare screenshots if baseline exists
    await expect(element).toHaveScreenshot(`baseline/${screenshotName}.png`, {
      maxDiffPixelRatio: 0.05,
    });
  }
  
  /**
   * Take a full page screenshot and compare with baseline
   */
  static async comparePageScreenshot(
    page: Page,
    screenshotName: string,
    updateBaseline: boolean = false
  ) {
    // Create directories if they don't exist
    const screenshotsDir = path.resolve('./test-results/screenshots');
    const baselineDir = path.join(screenshotsDir, 'baseline');
    const actualDir = path.join(screenshotsDir, 'actual');
    
    [screenshotsDir, baselineDir, actualDir].forEach(dir => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    });
    
    // File paths
    const baselinePath = path.join(baselineDir, `${screenshotName}.png`);
    const actualPath = path.join(actualDir, `${screenshotName}.png`);
    
    // Take full page screenshot
    await page.screenshot({ path: actualPath, fullPage: true });
    
    // If updating baseline or baseline doesn't exist, copy actual to baseline
    if (updateBaseline || !fs.existsSync(baselinePath)) {
      fs.copyFileSync(actualPath, baselinePath);
      return;
    }
    
    // Compare screenshots if baseline exists
    await expect(page).toHaveScreenshot(`baseline/${screenshotName}.png`, {
      maxDiffPixelRatio: 0.05,
      fullPage: true,
    });
  }
}
