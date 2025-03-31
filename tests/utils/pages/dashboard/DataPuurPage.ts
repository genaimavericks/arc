import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from '../BasePage';

/**
 * Page Object Model for the DataPuur component
 */
export class DataPuurPage extends BasePage {
  readonly datasetList: Locator;
  readonly uploadButton: Locator;
  readonly searchInput: Locator;
  readonly dataPreviewTable: Locator;
  readonly analyzeButton: Locator;

  constructor(page: Page) {
    super(page);
    this.datasetList = page.locator('[data-testid="dataset-list"]');
    this.uploadButton = page.locator('[data-testid="upload-dataset"]');
    this.searchInput = page.locator('[data-testid="search-datasets"]');
    this.dataPreviewTable = page.locator('[data-testid="data-preview-table"]');
    this.analyzeButton = page.locator('[data-testid="analyze-dataset"]');
  }

  async goto() {
    // Navigate to DataPuur section via dashboard
    await this.page.goto('/dashboard');
    await this.page.click('text=DataPuur');
    await this.waitForPageLoad();
  }

  async selectDataset(datasetName: string) {
    await this.searchInput.fill(datasetName);
    await this.page.locator(`text=${datasetName}`).first().click();
    // Wait for data preview to load
    await this.dataPreviewTable.waitFor({ state: 'visible' });
  }

  async uploadDataset(filePath: string) {
    const fileChooserPromise = this.page.waitForEvent('filechooser');
    await this.uploadButton.click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(filePath);
    
    // Wait for upload confirmation
    await this.page.locator('text=Upload complete').waitFor({ state: 'visible' });
  }

  async analyzeCurrentDataset() {
    await this.analyzeButton.click();
    // Wait for analysis to complete
    await this.page.locator('[data-testid="analysis-results"]').waitFor({ state: 'visible' });
  }

  async verifyDatasetExists(datasetName: string) {
    await this.searchInput.fill(datasetName);
    await expect(this.page.locator(`text=${datasetName}`).first()).toBeVisible();
  }
}
