import { test, expect } from '@playwright/test';

test.describe('Events Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/auth/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard');
  });

  test('should display events list', async ({ page }) => {
    await page.goto('/events');
    
    // Check if events page loads
    await expect(page.locator('h1')).toContainText('Events');
    
    // Events list should be visible
    await expect(page.locator('[data-testid="events-list"]')).toBeVisible();
  });

  test('should allow creating a new event', async ({ page }) => {
    await page.goto('/dashboard/events');
    
    // Click create event button
    await page.click('text=Create Event');
    
    // Fill event form
    await page.fill('input[name="title"]', 'Test Event');
    await page.fill('textarea[name="description"]', 'This is a test event description');
    await page.fill('input[name="location"]', 'Test Venue');
    
    // Set event date (future date)
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + 30);
    await page.fill('input[name="startDate"]', futureDate.toISOString().split('T')[0]);
    
    // Submit form
    await page.click('button[type="submit"]');
    
    // Should redirect to event details or events list
    await expect(page.url()).toMatch(/\/(events|dashboard)/);
    
    // Success message should appear
    await expect(page.locator('text=Event created successfully')).toBeVisible();
  });

  test('should allow viewing event details', async ({ page }) => {
    await page.goto('/events');
    
    // Click on first event (assuming there's at least one)
    await page.click('[data-testid="event-card"]:first-child');
    
    // Should navigate to event details page
    await expect(page.url()).toMatch(/\/events\/\d+/);
    
    // Event details should be visible
    await expect(page.locator('[data-testid="event-title"]')).toBeVisible();
    await expect(page.locator('[data-testid="event-description"]')).toBeVisible();
  });

  test('should allow searching events', async ({ page }) => {
    await page.goto('/events');
    
    // Use search functionality
    await page.fill('input[placeholder*="Search"]', 'Test Event');
    await page.press('input[placeholder*="Search"]', 'Enter');
    
    // Wait for search results
    await page.waitForTimeout(1000);
    
    // Results should be filtered
    await expect(page.locator('[data-testid="event-card"]')).toBeVisible();
  });

  test('should handle event creation validation', async ({ page }) => {
    await page.goto('/dashboard/events');
    await page.click('text=Create Event');
    
    // Try to submit empty form
    await page.click('button[type="submit"]');
    
    // Should show validation errors
    await expect(page.locator('text=Title is required')).toBeVisible();
    await expect(page.locator('text=Description is required')).toBeVisible();
  });

  test('should allow event organizer to edit their event', async ({ page }) => {
    await page.goto('/dashboard/events');
    
    // Click edit on first event (assuming user has events)
    await page.click('[data-testid="edit-event-button"]:first-child');
    
    // Update event title
    await page.fill('input[name="title"]', 'Updated Test Event');
    
    // Save changes
    await page.click('button[type="submit"]');
    
    // Success message should appear
    await expect(page.locator('text=Event updated successfully')).toBeVisible();
  });
});