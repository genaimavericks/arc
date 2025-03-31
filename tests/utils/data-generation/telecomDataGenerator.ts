import * as fs from 'fs';
import * as path from 'path';

/**
 * Generates synthetic telecom customer data for testing
 */
export class TelecomDataGenerator {
  /**
   * Generate a CSV file with telecom customer data
   * 
   * @param numRecords Number of records to generate
   * @param outputPath Path where the CSV file should be saved
   * @returns Full path to the generated file
   */
  static async generateTelecomData(numRecords: number, outputPath: string): Promise<string> {
    // Ensure the directory exists
    const dir = path.dirname(outputPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    
    // Generate CSV header
    const header = ['customer_id', 'name', 'age', 'subscription_type', 'monthly_charge'];
    const rows = [header.join(',')];
    
    // Generate data rows
    for (let i = 1; i <= numRecords; i++) {
      const customer_id = `CUST-${String(i).padStart(6, '0')}`;
      const name = `Customer ${i}`;
      const age = Math.floor(Math.random() * 50) + 18; // Age between 18 and 67
      
      // Random subscription type
      const subscriptionTypes = ['Basic', 'Standard', 'Premium', 'Enterprise'];
      const subscription_type = subscriptionTypes[Math.floor(Math.random() * subscriptionTypes.length)];
      
      // Monthly charge based on subscription type
      let baseCharge = 0;
      switch (subscription_type) {
        case 'Basic': baseCharge = 19.99; break;
        case 'Standard': baseCharge = 39.99; break;
        case 'Premium': baseCharge = 59.99; break;
        case 'Enterprise': baseCharge = 99.99; break;
      }
      const variance = (Math.random() * 10) - 5; // +/- $5
      const monthly_charge = (baseCharge + variance).toFixed(2);
      
      // Add the row to our data
      rows.push([customer_id, name, age, subscription_type, monthly_charge].join(','));
    }
    
    // Write to file
    fs.writeFileSync(outputPath, rows.join('\n'));
    
    return outputPath;
  }
  
  /**
   * Create test data directory and generate sample data files
   * 
   * @returns Object containing paths to generated files
   */
  static async setupTestData(): Promise<{telecomDataPath: string}> {
    // Create test data directory
    const testDataDir = path.resolve('./test-data/datasets');
    if (!fs.existsSync(testDataDir)) {
      fs.mkdirSync(testDataDir, { recursive: true });
    }
    
    // Generate telecom data file
    const telecomDataPath = path.join(testDataDir, 'telecom_customers.csv');
    await this.generateTelecomData(100, telecomDataPath);
    
    return {
      telecomDataPath
    };
  }
}
