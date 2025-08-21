import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Start fresh for each test
    await page.goto('/');
  });

  test('should allow user registration', async ({ page }) => {
    // Navigate to registration page
    await page.click('text=Register');
    await expect(page).toHaveURL('/auth/register');

    // Fill registration form
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.fill('input[name="confirmPassword"]', 'TestPassword123!');
    await page.fill('input[name="fullName"]', 'Test User');

    // Submit form
    await page.click('button[type="submit"]');

    // Should redirect to dashboard or login
    await expect(page.url()).toMatch(/\/(dashboard|auth\/login)/);
  });

  test('should allow user login', async ({ page }) => {
    // Navigate to login page
    await page.click('text=Login');
    await expect(page).toHaveURL('/auth/login');

    // Fill login form
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'TestPassword123!');

    // Submit form
    await page.click('button[type="submit"]');

    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard');
    
    // Check if user is logged in
    await expect(page.locator('text=Dashboard')).toBeVisible();
  });

  test('should handle login errors gracefully', async ({ page }) => {
    await page.goto('/auth/login');

    // Try to login with invalid credentials
    await page.fill('input[name="email"]', 'invalid@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    // Should show error message
    await expect(page.locator('text=Invalid credentials')).toBeVisible();
  });

  test('should validate registration form', async ({ page }) => {
    await page.goto('/auth/register');

    // Try to submit empty form
    await page.click('button[type="submit"]');

    // Should show validation errors
    await expect(page.locator('text=Email is required')).toBeVisible();
    await expect(page.locator('text=Password is required')).toBeVisible();
  });

  test('should allow user logout', async ({ page }) => {
    // First login
    await page.goto('/auth/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.click('button[type="submit"]');

    // Verify we're on dashboard
    await expect(page).toHaveURL('/dashboard');

    // Logout
    await page.click('text=Logout');

    // Should redirect to home page
    await expect(page).toHaveURL('/');
    
    // Login link should be visible again
    await expect(page.locator('text=Login')).toBeVisible();
  });
});