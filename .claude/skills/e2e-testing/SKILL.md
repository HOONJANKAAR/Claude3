---
name: e2e-testing
description: Playwright end-to-end testing patterns for this project — setup (not yet installed), Page Object Model, config, flaky-test fixes, and CI integration. Use when adding E2E tests for the chat UI or fixing flaky E2E runs.
---

# E2E Testing Patterns

This repo has **no E2E test suite yet** — only CRA's default unit test setup
(`src/App.test.js` via `react-scripts test`). Playwright is the recommended choice if/when
E2E coverage is added, since this is a plain SPA (React Router, one primary chat flow) with
no server-side rendering to complicate things.

## Setting Up (if not already done)

```bash
npm install --save-dev @playwright/test
npx playwright install --with-deps chromium   # add firefox/webkit if needed
```

Add scripts to `package.json`:

```json
{
  "scripts": {
    "test:e2e": "playwright test"
  }
}
```

## Suggested File Organization

```
e2e/
├── chat.spec.js
├── pages/
│   └── ChatPage.js        # Page Object for the chat screen
└── playwright.config.js
```

## Page Object Model

```javascript
// e2e/pages/ChatPage.js
export class ChatPage {
  constructor(page) {
    this.page = page;
    this.input = page.getByLabel('Chat message');
    this.sendButton = page.getByRole('button', { name: /send/i });
    this.messages = page.getByTestId('chat-message');
  }

  async goto() {
    await this.page.goto('/');
  }

  async sendMessage(text) {
    await this.input.fill(text);
    await this.sendButton.click();
  }
}
```

## Test Structure

```javascript
// e2e/chat.spec.js
import { test, expect } from '@playwright/test';
import { ChatPage } from './pages/ChatPage';

test.describe('Chat flow', () => {
  test('sends a message and sees it in the history', async ({ page }) => {
    const chat = new ChatPage(page);
    await chat.goto();

    await chat.sendMessage('Hello');

    await expect(chat.messages.last()).toContainText('Hello');
  });

  test('shows an error when the API call fails', async ({ page }) => {
    // Mock the Puter API call at the network layer instead of hitting it for real
    await page.route('**/ai/chat', route =>
      route.fulfill({ status: 500, body: JSON.stringify({ error: 'server error' }) })
    );

    const chat = new ChatPage(page);
    await chat.goto();
    await chat.sendMessage('Hello');

    await expect(page.getByText(/failed to get a response/i)).toBeVisible();
  });
});
```

## Playwright Config

```javascript
// playwright.config.js
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [['html', { outputFolder: 'playwright-report' }]],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'npm start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
```

## Avoiding Flaky Tests

```javascript
// BAD: arbitrary timeout, especially bad for a streaming chat response
await page.waitForTimeout(2000);

// GOOD: wait for a specific network response or UI state
await page.waitForResponse(resp => resp.url().includes('/ai/chat'));
await expect(page.getByTestId('streaming-cursor')).toBeHidden();
```

```javascript
// BAD: click before the element is guaranteed interactive
await page.click('[data-testid="send-button"]');

// GOOD: locator auto-waits for actionability
await page.getByRole('button', { name: /send/i }).click();
```

To hunt down a suspected flaky test:

```bash
npx playwright test e2e/chat.spec.js --repeat-each=10
```

## CI Integration

```yaml
# .github/workflows/e2e.yml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - run: npx playwright install --with-deps chromium
      - run: npx playwright test
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

**Remember**: this app talks to an external API (Puter) directly from the browser — mock
that network call at the `page.route()` level for E2E tests rather than hitting the real
service, both for reliability and to avoid burning real API quota in CI.
