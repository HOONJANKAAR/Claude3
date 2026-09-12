---
name: coding-standards
description: Baseline coding conventions for this project — naming, readability, immutability, error handling, and code-quality review. Use `frontend-patterns` for React-specific composition, hooks, and rendering concerns. Use when reviewing code quality or naming and no more specific skill applies.
---

# Coding Standards & Best Practices

Baseline conventions for this repo. This is plain JavaScript (no TypeScript, no build-time
type checker) on Create React App (`react-scripts`), so lean on runtime checks, PropTypes-style
diligence, and tests rather than a type system to catch mistakes.

This skill is the shared floor, not the React playbook — use `frontend-patterns` for
component composition, hooks, and rendering.

## When to Activate

- Starting a new component, hook, or service module
- Reviewing code for quality and maintainability
- Refactoring existing code to follow conventions
- Enforcing naming, formatting, or structural consistency

## Code Quality Principles

### 1. Readability First
Code is read far more than it's written. Prefer clear names and self-documenting code over
comments explaining what the code does — reserve comments for *why*.

### 2. KISS / DRY / YAGNI
- Simplest solution that works; no premature optimization.
- Extract repeated logic into a shared function, hook, or component (e.g. shared UI bits
  belong in `src/components/`, shared logic in `src/hooks/`).
- Don't build configurability or abstraction the app doesn't need yet.

## JavaScript Standards

### Variable & Function Naming

```javascript
// GOOD: descriptive names, verb-noun functions
const chatHistory = [];
const isStreaming = true;

async function fetchModelResponse(input, model) { }
function formatTimestamp(date) { }

// BAD: unclear names
const h = [];
const flag = true;
async function get(i, m) { }
```

### Immutability (CRITICAL — this app is state/hook heavy)

```javascript
// GOOD: never mutate state directly
setMessages(prev => [...prev, newMessage]);
setUser(prev => ({ ...prev, name: 'New Name' }));

// BAD: mutates in place, won't trigger a re-render reliably
messages.push(newMessage);
user.name = 'New Name';
```

### Error Handling

Every network call (this app talks to the Puter API via `axios` in `src/services/`) needs
explicit error handling — don't let a rejected promise surface as an unhandled console error
in the UI.

```javascript
// GOOD
export const fetchModelResponse = async (input, model) => {
  try {
    const response = await axios.post(`${BASE_URL}/ai/chat`, { prompt: input, model });
    return response.data;
  } catch (error) {
    console.error('fetchModelResponse failed:', error);
    throw new Error('Failed to get a response. Please try again.');
  }
};

// BAD: no error handling — a network failure crashes the calling component silently
export const fetchModelResponse = async (input, model) => {
  const response = await axios.post(`${BASE_URL}/ai/chat`, { prompt: input, model });
  return response.data;
};
```

### Async/Await

```javascript
// GOOD: parallel when requests are independent
const [history, settings] = await Promise.all([loadHistory(), loadSettings()]);

// BAD: sequential when there's no dependency between them
const history = await loadHistory();
const settings = await loadSettings();
```

## React Component Conventions

```javascript
// GOOD: clear props, sensible defaults, no unused props
export function ChatMessage({ message, sender, timestamp, isStreaming = false }) {
  return (
    <div className={`chat-message ${sender}`}>
      <p>{message}</p>
      {isStreaming && <span className="cursor" />}
    </div>
  );
}

// BAD: an opaque `props` blob, no defaults, unclear what's required
export function ChatMessage(props) {
  return <div>{props.message}</div>;
}
```

### Conditional Rendering

```javascript
// GOOD
{isLoading && <Spinner />}
{error && <ErrorMessage error={error} />}
{!isLoading && !error && <ChatHistory messages={messages} />}

// BAD: ternary chains that are hard to scan
{isLoading ? <Spinner /> : error ? <ErrorMessage error={error} /> : <ChatHistory messages={messages} />}
```

## File Organization (as used in `src/`)

```
src/
├── components/     # Presentational + composed UI components
├── pages/          # Route-level components (ChatPage, etc.)
├── hooks/          # Custom hooks (usePuterScript, etc.)
├── services/       # API clients (axios calls out to Puter)
├── styles/         # Theme and shared styling (MUI theme.js)
```

- Components: `PascalCase.js` (`ChatMessage.js`)
- Hooks: `camelCase.js` starting with `use` (`usePuterScript.js`)
- Services/utilities: `camelCase.js` (`api.js`)

## Comments

```javascript
// GOOD: explains WHY
// Puter's streaming endpoint sends partial JSON chunks — buffer until a full line arrives.
const line = buffer.split('\n').pop();

// BAD: states the obvious
// increment count by 1
count++;
```

## Performance

```javascript
import { useMemo, useCallback } from 'react';

// Memoize expensive derived data
const sortedHistory = useMemo(() => [...history].sort((a, b) => b.timestamp - a.timestamp), [history]);

// Memoize callbacks passed to memoized children
const handleSend = useCallback((text) => sendMessage(text), [sendMessage]);
```

## Code Smells to Flag in Review

- **Long functions** (>~50 lines) — split into smaller named steps.
- **Deep nesting** — prefer early returns over pyramids of `if`.
- **Magic numbers/strings** — name them (`const STREAM_CHUNK_DELAY_MS = 50`), especially for
  timeouts, retry counts, and model identifiers.
- **Direct DOM/state mutation** — always go through `setState` with a new reference.

**Remember**: readable, testable code here means fewer regressions in the chat flow — this is
a small app, but the same discipline still pays off.
