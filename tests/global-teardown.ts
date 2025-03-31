import { FullConfig } from '@playwright/test';
import * as childProcess from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

/**
 * Global teardown function to stop the RSW servers after testing
 */
async function globalTeardown(config: FullConfig) {
  console.log('Stopping RSW test servers...');
  
  // Get path to script
  const scriptPath = path.join(process.cwd(), 'stop-test-servers.sh');
  
  if (!fs.existsSync(scriptPath)) {
    console.error(`Stop script not found at ${scriptPath}`);
    return;
  }
  
  // Run the script to stop servers
  console.log('Executing stop-test-servers.sh...');
  try {
    childProcess.execSync(scriptPath, { stdio: 'inherit' });
    console.log('Servers stopped successfully!');
  } catch (error) {
    console.error('Error stopping servers:', error);
  }
  
  // Give some time for processes to fully terminate
  await new Promise(resolve => setTimeout(resolve, 1000));
}

export default globalTeardown;
