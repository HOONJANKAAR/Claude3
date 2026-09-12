---
name: tdd-workflow
description: Test-driven development workflow for this project. Use when writing new features, fixing bugs, or refactoring components/hooks/services — write tests first, then implement, using this project's CRA/Jest + React Testing Library setup.
---

# Test-Driven Development Workflow

This app uses **Create React App**'s built-in test runner (`react-scripts test`, which wraps
Jest) with **React Testing Library** (`@testing-library/react`, `@testing-library/jest-dom`,
`@testing-library/user-event` are already installed). Package manager is **npm**
(`package-lock.json` is committed) — always run through it:

| Purpose | Command |
|---|---|
| Run tests once | `CI=true npm test -- --watchAll=false` |
| Watch mode (default `npm test`) | `npm test` |
| Coverage | `CI=true npm test -- --coverage --watchAll=false` |
| Lint | no separate lint script is configured yet — ESLint runs as part of `react-scripts start`/`build` via the `eslintConfig` in `package.json` |

`npm test` alone drops into Jest's interactive watch mode, which hangs in a non-interactive
shell — always pass `CI=true ... --watchAll=false` (or use `npm test -- --watchAll=false`)
when running once, e.g. before committing.

## Core Principles

1. **Tests before code.** Write a failing test that expresses the desired behavior, then
   implement until it passes.
2. **Test user-visible behavior, not internals.** Query by role/label/text the way a user
   would, not component state or implementation details.
3. **Cover the paths that matter for a chat app**: sending a message, receiving/streaming a
   response, error/loading states, and empty states — not just the happy path.

## Workflow

### Step 1: Describe the behavior

```
As a user, I want to send a chat message and see it appear in the history,
so that I can have a conversation with the model.
```

### Step 2: Write the test first

```javascript
// src/components/ChatInput.test.js
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatInput from './ChatInput';

describe('ChatInput', () => {
  it('calls onSend with the typed message when Enter is pressed', async () => {
    const handleSend = jest.fn();
    render(<ChatInput onSend={handleSend} />);

    const input = screen.getByLabelText(/chat message/i);
    await userEvent.type(input, 'Hello{Enter}');

    expect(handleSend).toHaveBeenCalledWith('Hello');
  });

  it('does not call onSend for an empty message', async () => {
    const handleSend = jest.fn();
    render(<ChatInput onSend={handleSend} />);

    await userEvent.type(screen.getByLabelText(/chat message/i), '{Enter}');

    expect(handleSend).not.toHaveBeenCalled();
  });
});
```

### Step 3: Run it — it should fail

```bash
CI=true npm test -- --watchAll=false ChatInput
```

### Step 4: Implement the minimal code to pass

### Step 5: Re-run — it should pass, then refactor with tests green

## Testing Patterns for This App

### Component test (React Testing Library)

```javascript
import { render, screen, fireEvent } from '@testing-library/react';
import ChatMessage from './ChatMessage';

test('renders the message text', () => {
  render(<ChatMessage message="Hi there" sender="user" />);
  expect(screen.getByText('Hi there')).toBeInTheDocument();
});

test('shows a streaming indicator while isStreaming is true', () => {
  render(<ChatMessage message="" sender="assistant" isStreaming />);
  expect(screen.getByTestId('streaming-cursor')).toBeInTheDocument();
});
```

### Mocking the API layer (`src/services/api.js`)

```javascript
jest.mock('../services/api', () => ({
  fetchModelResponse: jest.fn(),
}));

import { fetchModelResponse } from '../services/api';

test('shows an error message when the API call fails', async () => {
  fetchModelResponse.mockRejectedValueOnce(new Error('network error'));

  render(<ChatPage />);
  fireEvent.click(screen.getByRole('button', { name: /send/i }));

  expect(await screen.findByText(/failed to get a response/i)).toBeInTheDocument();
});
```

### Mocking `axios` directly (for `src/services/*.js` unit tests)

```javascript
jest.mock('axios');
import axios from 'axios';
import { fetchModelResponse } from './api';

test('posts the prompt and model to the chat endpoint', async () => {
  axios.post.mockResolvedValueOnce({ data: { reply: 'hi' } });

  const result = await fetchModelResponse('hello', 'model1');

  expect(axios.post).toHaveBeenCalledWith(
    expect.stringContaining('/ai/chat'),
    expect.objectContaining({ prompt: 'hello' })
  );
  expect(result).toEqual({ reply: 'hi' });
});
```

## Test File Organization

CRA convention — colocate tests next to the file they cover:

```
src/
├── components/
│   ├── ChatMessage.js
│   └── ChatMessage.test.js
├── hooks/
│   ├── usePuterScript.js
│   └── usePuterScript.test.js
├── services/
│   ├── api.js
│   └── api.test.js
```

## Common Mistakes to Avoid

```javascript
// BAD: testing implementation details
expect(wrapper.state('count')).toBe(5);

// GOOD: testing what the user sees
expect(screen.getByText('Count: 5')).toBeInTheDocument();
```

```javascript
// BAD: brittle selector
container.querySelector('.css-1a2b3c');

// GOOD: resilient, accessible selector
screen.getByRole('button', { name: /send/i });
```

```javascript
// BAD: tests depend on shared mutable state
let sharedUser;
test('creates user', () => { sharedUser = createUser(); });
test('updates user', () => { updateUser(sharedUser); }); // depends on previous test running first

// GOOD: each test is independent
test('updates user', () => {
  const user = createUser();
  updateUser(user);
});
```

## Notes on Coverage

There's no enforced coverage threshold configured in this repo yet. If you want to add one,
it goes in `package.json` under a `jest` key (CRA merges it with its own Jest config):

```json
{
  "jest": {
    "coverageThreshold": {
      "global": { "branches": 70, "functions": 70, "lines": 70, "statements": 70 }
    }
  }
}
```

Don't add this without checking existing coverage first (`CI=true npm test -- --coverage
--watchAll=false`) — an unrealistic threshold just blocks CI.

**Remember**: write the test for the behavior you're about to build, watch it fail, then make
it pass — that loop catches regressions in the chat flow far earlier than manual clicking
through the UI.
