import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from '../BasePage';

/**
 * Page Object Model for the KGInsight component
 */
export class KGInsightPage extends BasePage {
  readonly graphVisualization: Locator;
  readonly nodeList: Locator;
  readonly relationshipList: Locator;
  readonly searchInput: Locator;
  readonly filterPanel: Locator;
  readonly createNodeButton: Locator;
  readonly createRelationshipButton: Locator;

  constructor(page: Page) {
    super(page);
    this.graphVisualization = page.locator('[data-testid="graph-visualization"]');
    this.nodeList = page.locator('[data-testid="node-list"]');
    this.relationshipList = page.locator('[data-testid="relationship-list"]');
    this.searchInput = page.locator('[data-testid="search-graph"]');
    this.filterPanel = page.locator('[data-testid="filter-panel"]');
    this.createNodeButton = page.locator('[data-testid="create-node"]');
    this.createRelationshipButton = page.locator('[data-testid="create-relationship"]');
  }

  async goto() {
    // Navigate to KGInsight section via dashboard
    await this.page.goto('/dashboard');
    await this.page.click('text=KGInsight');
    await this.waitForPageLoad();
  }

  async verifyGraphLoaded() {
    await this.graphVisualization.waitFor({ state: 'visible' });
    await expect(this.page.locator('[data-testid="graph-loading"]')).not.toBeVisible();
  }

  async searchGraph(query: string) {
    await this.searchInput.fill(query);
    await this.page.keyboard.press('Enter');
    // Wait for search results
    await this.waitForPageLoad();
  }

  async selectNode(nodeName: string) {
    await this.searchInput.fill(nodeName);
    await this.page.locator(`text=${nodeName}`).first().click();
    // Wait for node details to load
    await this.page.locator('[data-testid="node-details"]').waitFor({ state: 'visible' });
  }

  async createNewNode(nodeType: string, properties: Record<string, string>) {
    await this.createNodeButton.click();
    await this.page.locator('[data-testid="node-type-select"]').selectOption(nodeType);
    
    // Fill node properties
    for (const [key, value] of Object.entries(properties)) {
      await this.page.locator(`[data-testid="property-${key}"]`).fill(value);
    }
    
    // Save the node
    await this.page.locator('[data-testid="save-node"]').click();
    // Wait for confirmation
    await this.page.locator('text=Node created successfully').waitFor({ state: 'visible' });
  }

  async createRelationship(sourceNodeName: string, targetNodeName: string, relationshipType: string) {
    // First select source node
    await this.selectNode(sourceNodeName);
    
    // Click create relationship button
    await this.createRelationshipButton.click();
    
    // Set target node
    await this.page.locator('[data-testid="target-node-input"]').fill(targetNodeName);
    await this.page.keyboard.press('Enter');
    
    // Select relationship type
    await this.page.locator('[data-testid="relationship-type-select"]').selectOption(relationshipType);
    
    // Save the relationship
    await this.page.locator('[data-testid="save-relationship"]').click();
    
    // Wait for confirmation
    await this.page.locator('text=Relationship created successfully').waitFor({ state: 'visible' });
  }
}
