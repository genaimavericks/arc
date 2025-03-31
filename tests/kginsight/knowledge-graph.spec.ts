import { test, expect } from '@playwright/test';
import { login } from '../utils/auth';
import { KGInsightPage } from '../utils/pages/dashboard/KGInsightPage';
import { users, knowledgeGraphs } from '../utils/data/testData';

test.describe('KGInsight Knowledge Graph', () => {
  let kgInsightPage: KGInsightPage;

  test.beforeEach(async ({ page }) => {
    // Login with admin user through hero page
    await login(page, 'admin', 'admin123');
    
    // Initialize the KGInsight page
    kgInsightPage = new KGInsightPage(page);
    await kgInsightPage.goto();
  });

  test('should display graph visualization', async ({ page }) => {
    // Verify the graph visualization loads
    await kgInsightPage.verifyGraphLoaded();
    
    // Verify nodes are visible in the visualization
    await expect(page.locator('[data-testid="graph-node"]')).toBeVisible();
  });

  test('should create a new node', async ({ page }) => {
    // Create a test node
    const nodeProps = {
      'name': 'Test Customer',
      'age': '35',
      'subscription': 'Premium'
    };
    
    await kgInsightPage.createNewNode('Customer', nodeProps);
    
    // Search for the newly created node
    await kgInsightPage.searchGraph('Test Customer');
    
    // Verify node appears in search results
    await expect(page.locator('text=Test Customer')).toBeVisible();
  });

  test('should create a relationship between nodes', async ({ page }) => {
    // Create source and target nodes if they don't exist
    const sourceNodeProps = { 'name': 'Test Service' };
    const targetNodeProps = { 'name': 'Test Customer' };
    
    await kgInsightPage.createNewNode('Service', sourceNodeProps);
    await kgInsightPage.createNewNode('Customer', targetNodeProps);
    
    // Create relationship
    await kgInsightPage.createRelationship('Test Service', 'Test Customer', 'SUBSCRIBES_TO');
    
    // Verify relationship exists
    await kgInsightPage.searchGraph('Test Service');
    await expect(page.locator('[data-testid="relationship-SUBSCRIBES_TO"]')).toBeVisible();
  });
});
