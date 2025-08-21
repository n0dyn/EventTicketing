import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting E2E test setup...');
  
  // Wait for backend to be ready
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    // Check if backend is healthy
    await page.goto('http://localhost:8000/health', { 
      waitUntil: 'networkidle',
      timeout: 10000 
    });
    
    const response = await page.textContent('body');
    const healthCheck = JSON.parse(response || '{}');
    
    if (healthCheck.status !== 'healthy') {
      throw new Error('Backend health check failed');
    }
    
    console.log('✅ Backend is healthy');
    
    // Check if frontend is ready
    await page.goto('http://localhost:3000', { 
      waitUntil: 'networkidle',
      timeout: 10000 
    });
    
    console.log('✅ Frontend is accessible');
    
  } catch (error) {
    console.error('❌ Setup failed:', error);
    throw error;
  } finally {
    await browser.close();
  }
  
  console.log('✅ E2E test setup completed');
}

export default globalSetup;