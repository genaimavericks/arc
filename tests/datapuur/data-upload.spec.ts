import { test, expect } from '@playwright/test';
import { login } from '../utils/auth';
import { DataPuurPage } from '../utils/pages/dashboard/DataPuurPage';
import { users, dataSets } from '../utils/data/testData';

test.describe('DataPuur Data Upload', () => {
  let dataPuurPage: DataPuurPage;

  test.beforeEach(async ({ page }) => {
    // Login with admin user (now goes through hero page)
    await login(page, 'admin', 'admin123');
    
    // Initialize the DataPuur page
    dataPuurPage = new DataPuurPage(page);
    await dataPuurPage.goto();
  });

  test('should upload a new dataset', async ({ page }) => {
    // Create a test file path based on the test data
    const testFilePath = `./test-data${dataSets.telecom.path}`;
    
    // Upload the dataset
    await dataPuurPage.uploadDataset(testFilePath);
    
    // Verify the dataset appears in the list
    await dataPuurPage.verifyDatasetExists(dataSets.telecom.name);
  });

  test('should preview data from uploaded dataset', async ({ page }) => {
    // Select the dataset
    await dataPuurPage.selectDataset(dataSets.telecom.name);
    
    // Verify data preview is shown
    await expect(dataPuurPage.dataPreviewTable).toBeVisible();
    
    // Verify the data has the expected columns
    for (const column of dataSets.telecom.columns) {
      await expect(page.locator(`th:has-text("${column}")`)).toBeVisible();
    }
  });

  test('should analyze a dataset', async ({ page }) => {
    // Select the dataset
    await dataPuurPage.selectDataset(dataSets.telecom.name);
    
    // Run analysis
    await dataPuurPage.analyzeCurrentDataset();
    
    // Verify analysis results appear
    await expect(page.locator('[data-testid="analysis-results"]')).toBeVisible();
    
    // Check for common analysis components (charts, statistics)
    await expect(page.locator('[data-testid="data-statistics"]')).toBeVisible();
    await expect(page.locator('[data-testid="data-visualization"]')).toBeVisible();
  });
});
