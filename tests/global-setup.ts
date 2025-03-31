import { FullConfig } from '@playwright/test';
import * as childProcess from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

// Declare global variable to store server process
declare global {
  var __TEST_SERVER_PROC__: childProcess.ChildProcess | undefined;
}

/**
 * Global setup function to start the RSW servers for testing
 */
async function globalSetup(config: FullConfig) {
  console.log('Starting RSW servers for testing...');
  
  // Set environment variables for testing
  // Using SQLite by default for tests (based on db_config.py support)
  process.env.DB_TYPE = 'sqlite';
  
  // Create required directories for Playwright tests
  const requiredDirs = [
    path.join(process.cwd(), 'test-results'),
    path.join(process.cwd(), 'playwright-report'),
    path.join(process.cwd(), 'test-results/screenshots'),
    path.join(process.cwd(), 'test-results/screenshots/baseline'),
    path.join(process.cwd(), 'test-results/screenshots/actual'),
    path.join(process.cwd(), 'test-results/screenshots/diff')
  ];
  
  // Create each directory if it doesn't exist
  for (const dir of requiredDirs) {
    if (!fs.existsSync(dir)) {
      console.log(`Creating directory: ${dir}`);
      fs.mkdirSync(dir, { recursive: true });
    }
  }
  
  // Get path to script
  /*const scriptPath = path.join(process.cwd(), 'start-test-servers.sh');
  
  if (!fs.existsSync(scriptPath)) {
    console.error(`Start script not found at ${scriptPath}`);
    process.exit(1);
  }
  
  // Run the script to start servers (don't wait for it to finish)
  console.log('Executing start-test-servers.sh...');
  const proc = childProcess.spawn(scriptPath, [], {
    stdio: 'inherit',
    shell: true
  });
  
  // Store process reference for teardown
  global.__TEST_SERVER_PROC__ = proc;
  
  // Give servers time to start
  console.log('Waiting for servers to start up completely...');
  await new Promise(resolve => setTimeout(resolve, 5000));
  
  // Verify servers are running by checking the PID file
  const pidFilePath = path.join(process.cwd(), 'test-servers.pid');
  if (fs.existsSync(pidFilePath)) {
    console.log('Servers started successfully!');
  } else {
    console.error('Servers may not have started properly. Check logs.');
  }
} */

export default globalSetup;
