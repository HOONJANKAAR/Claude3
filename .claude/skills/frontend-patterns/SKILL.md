---
name: frontend-patterns
description: React frontend patterns for this project — component composition, hooks, state, MUI theming, Framer Motion animation, and accessibility. Use when building or reviewing React components, hooks, or UI rendering/performance in this app.
---

# Frontend Development Patterns

React patterns tailored to this app's actual stack: React 19 (function components + hooks
only, no class components except error boundaries), MUI v6 for UI, Framer Motion for
animation, React Router v7, and plain JavaScript (no TypeScript, no Next.js — this is a
Create React App SPA).

## Privacy and Data Boundaries

Chat content and any future user data are potentially sensitive. Don't log full prompt/response
bodies to third-party services, don't add analytics/tracking without explicit approval, and
never persist API keys or tokens in client-side storage that isn't necessary — this app calls
the Puter API directly from the browser, so treat anything callable from `src/services/api.js`
as public-network-facing.

## Component Patterns

### Composition Over Props Explosion

```javascript
// GOOD: composable pieces
export function Card({ children, variant = 'default' }) {
  return <div className={`card card-${variant}`}>{children}</div>;
}
export function CardHeader({ children }) {
  return <div className="card-header">{children}</div>;
}

// Usage
<Card>
  <CardHeader>Chat History</CardHeader>
  <ChatHistory messages={messages} />
</Card>
```

### Container/Presentational Split

Keep data-fetching and state (e.g. `ChatPage.js`) separate from pure rendering
(`ChatMessage.js`, `ChatHistory.js`). Presentational components should be easy to unit test
without mocking network calls.

## Custom Hooks

This app already has `usePuterScript` — follow the same shape for new hooks: encapsulate a
side effect + expose simple state.

```javascript
// GOOD: a debounce hook, useful for chat input / search-as-you-type
export function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}
```

```javascript
// GOOD: async fetch hook with stable refetch, avoiding infinite-loop pitfalls
export function useAsync(fetcher, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true });

  useEffect(() => {
    let cancelled = false;
    setState(s => ({ ...s, loading: true }));

    fetcher()
      .then(data => !cancelled && setState({ data, error: null, loading: false }))
      .catch(error => !cancelled && setState({ data: null, error, loading: false }));

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
```

## State Management

This app doesn't use Redux/Zustand — `useState`/`useReducer` + prop drilling or Context is
enough at this size. Reach for `useReducer` once a component has more than ~3 related state
values that change together (e.g. chat: `messages`, `isStreaming`, `error`).

```javascript
function chatReducer(state, action) {
  switch (action.type) {
    case 'SEND_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload], isStreaming: true };
    case 'RECEIVE_CHUNK':
      return { ...state, isStreaming: false };
    case 'ERROR':
      return { ...state, error: action.payload, isStreaming: false };
    default:
      return state;
  }
}
```

## MUI Patterns

Use the shared theme from `src/styles/theme.js` rather than inline colors — keep the app's
look consistent and dark/light-mode-ready.

```javascript
import { useTheme } from '@mui/material/styles';

function Header() {
  const theme = useTheme();
  return <AppBar sx={{ bgcolor: theme.palette.background.paper }}>...</AppBar>;
}
```

Prefer the `sx` prop over separate CSS files for component-scoped styling; reserve `App.css`
/ `index.css` for truly global rules.

## Framer Motion (already a dependency)

```javascript
import { motion, AnimatePresence } from 'framer-motion';

export function AnimatedMessageList({ messages }) {
  return (
    <AnimatePresence>
      {messages.map(m => (
        <motion.div
          key={m.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
        >
          <ChatMessage {...m} />
        </motion.div>
      ))}
    </AnimatePresence>
  );
}
```

## Performance

```javascript
import { useMemo, useCallback, lazy, Suspense } from 'react';

// Memoize expensive derived lists
const sortedHistory = useMemo(() => [...history].sort((a, b) => b.timestamp - a.timestamp), [history]);

// Lazy-load rarely-visited routes/pages
const SettingsPage = lazy(() => import('./pages/SettingsPage'));

<Suspense fallback={<Spinner />}>
  <SettingsPage />
</Suspense>
```

Long chat histories (hundreds of messages) are the one place in this app virtualization would
matter — reach for a library like `react-window` only if profiling actually shows a problem;
don't add it preemptively.

## Error Boundary

```javascript
export class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error boundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-fallback">
          <h2>Something went wrong</h2>
          <button onClick={() => this.setState({ hasError: false })}>Try again</button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

## Accessibility

- Every interactive element needs a keyboard path (`Enter`/`Space` to activate, `Escape` to
  dismiss modals/menus) and a visible focus state — MUI components mostly handle this, but
  custom `div`s with `onClick` do not.
- Give the chat input and send button proper labels (`aria-label`) since they're the app's
  primary interaction.

```javascript
<input
  aria-label="Chat message"
  value={input}
  onChange={e => setInput(e.target.value)}
  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
/>
```

**Remember**: this is a small SPA — favor the simplest pattern that solves the problem at
hand over introducing new state libraries, CSS-in-JS systems, or data-fetching frameworks.
