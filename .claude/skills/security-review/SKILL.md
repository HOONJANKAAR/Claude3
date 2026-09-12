---
name: security-review
description: Security checklist for this project's specific shape — a client-only React SPA that calls a third-party AI API (Puter) directly from the browser. Use when touching src/services/api.js, adding auth, rendering model output as HTML, or before a release.
---

# Security Review Skill

This app has **no backend of its own** — it's a static SPA (Create React App) that calls the
Puter API (`https://api.puter.com`) directly from the browser via `axios`, and loads the
Puter.js SDK (`https://js.puter.com/v2/`) for auth. That shape changes which checks matter:
there's no SQL injection surface or server-side session to protect here, but everything
shipped to `src/` is public and inspectable by anyone who opens dev tools.

## When to Activate

- Editing `src/services/api.js` or anything else that calls out to Puter or another API
- Adding authentication/login
- Rendering model output as anything other than plain text (e.g. adding markdown/HTML rendering)
- Adding a form that collects user input beyond the chat box
- Before a release/deploy

## 1. No Secrets in Client Code

Everything in `src/` ends up in the built JS bundle and is visible to any visitor — there is
no server step to hide values.

```javascript
// NEVER: a real secret baked into client code
const apiKey = 'sk-live-xxxxxxxxxxxx';

// If a key must be used from the browser, it must be a key meant to be public
// (rate-limited, scoped, revocable) — never a private/server-side secret.
```

- [ ] No API keys, tokens, or credentials hardcoded anywhere under `src/`
- [ ] `.env.local` / `.env*.local` stay in `.gitignore` (already the case — verify before adding new env files)
- [ ] `git log -p` doesn't contain a secret that was later removed but still lives in history
- [ ] Puter auth is handled via the Puter.js SDK's own flow (`usePuterScript`), not a stored token in `localStorage`/source

## 2. Rendering Model Output Safely

Model responses are untrusted text. Right now `ChatMessage` renders them as plain text
(React escapes this by default — safe). **If markdown or HTML rendering is ever added**, that
protection goes away and needs to be re-established explicitly:

```javascript
// DANGEROUS if `content` can contain attacker- or model-influenced HTML/script
<div dangerouslySetInnerHTML={{ __html: content }} />

// SAFE: render as text (React escapes it)
<div>{content}</div>

// SAFE: if markdown is genuinely needed, sanitize after converting
import DOMPurify from 'dompurify';
const clean = DOMPurify.sanitize(markdownToHtml(content));
<div dangerouslySetInnerHTML={{ __html: clean }} />
```

- [ ] No `dangerouslySetInnerHTML` without a sanitizer (grep for it before merging: `grep -rn dangerouslySetInnerHTML src/`)
- [ ] User-typed input and model output are both treated as untrusted

## 3. Input Validation

```javascript
// GOOD: bound the chat input before sending it out
function isSendable(message) {
  return typeof message === 'string' && message.trim().length > 0 && message.length <= 4000;
}
```

- [ ] Empty/whitespace-only messages are rejected client-side
- [ ] There's a sane upper bound on message length before it's sent to the API
- [ ] Any future file-upload feature validates size/type before upload, not just extension

## 4. Network & Error Handling

```javascript
// BAD: leaks internal error detail (stack traces, raw axios error) to the UI
catch (error) {
  setErrorMessage(error.stack);
}

// GOOD: log detail for debugging, show a generic message to the user
catch (error) {
  console.error('fetchModelResponse failed:', error);
  setErrorMessage('Something went wrong. Please try again.');
}
```

- [ ] Errors shown in the UI are generic; full error detail only goes to `console.error`
- [ ] Requests to the Puter API go over HTTPS (already true — `BASE_URL` uses `https://`)
- [ ] Don't log full prompt/response content to any third-party analytics/logging service

## 5. Dependency Hygiene

```bash
npm audit          # check for known vulnerabilities
npm audit fix       # apply safe automatic fixes
npm outdated        # see what's behind
```

- [ ] `npm audit` is clean (or documented exceptions) before a release
- [ ] `package-lock.json` is committed and used in CI (`npm ci`, not `npm install`)
- [ ] Dependabot or equivalent is enabled on the GitHub repo

## 6. If Auth/Accounts Are Added Later

This app doesn't currently have user accounts beyond whatever Puter's own SDK handles. If
first-party auth is added:

- [ ] Session tokens go in `httpOnly` cookies, never `localStorage` (XSS-readable)
- [ ] Every authenticated request is checked server-side (once there is a server) — client-side
      checks alone are not authorization
- [ ] Rate limiting is added once there's a backend that can enforce it (the browser can't
      enforce its own rate limits against abuse)

## Pre-Release Checklist

- [ ] No hardcoded secrets in `src/`
- [ ] No unsanitized `dangerouslySetInnerHTML`
- [ ] Chat input validated (non-empty, bounded length)
- [ ] Errors shown to users are generic; details stay in console/logs
- [ ] `npm audit` clean
- [ ] `package-lock.json` committed, CI uses `npm ci`

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [React: Dangerously Set innerHTML](https://react.dev/reference/react-dom/components/common#dangerously-setting-the-inner-html)

**Remember**: there's no server here to catch what the client misses — anything that must be
secret can't live in this codebase at all, and anything rendered from untrusted text needs to
go through React's default escaping (or an explicit sanitizer, never raw HTML) to stay safe.
