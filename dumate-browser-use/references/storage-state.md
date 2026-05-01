# Storage Management

## Storage State

Save and restore complete browser state including cookies and storage.

### Save Storage State
```bash
# Save to auto-generated filename (storage-state-{timestamp}.json)
playwright-cli state-save

# Save to specific filename
playwright-cli state-save my-auth-state.json
```

### Restore Storage State
```bash
# Load storage state from file
playwright-cli state-load my-auth-state.json

# Reload page to apply cookies
playwright-cli open https://example.com
```

### Storage State File Format
```json
{
  "cookies": [{ "name": "session_id", "value": "abc123", "domain": "example.com",
    "path": "/", "expires": 1735689600, "httpOnly": true, "secure": true, "sameSite": "Lax" }],
  "origins": [{ "origin": "https://example.com",
    "localStorage": [{ "name": "theme", "value": "dark" }, { "name": "user_id", "value": "12345" }] }]
}
```

---

## Cookies

| Command | Example |
|---|---|
| List all | `playwright-cli cookie-list` |
| Filter by domain | `playwright-cli cookie-list --domain=example.com` |
| Filter by path | `playwright-cli cookie-list --path=/api` |
| Get specific | `playwright-cli cookie-get session_id` |
| Delete | `playwright-cli cookie-delete session_id` |
| Clear all | `playwright-cli cookie-clear` |

### Set a Cookie
```bash
playwright-cli cookie-set session abc123
playwright-cli cookie-set session abc123 --domain=example.com --path=/ --httpOnly --secure --sameSite=Lax
playwright-cli cookie-set remember_me token123 --expires=1735689600
```

### Advanced: Multiple Cookies
```bash
playwright-cli run-code "async page => {
  await page.context().addCookies([
    { name: 'session_id', value: 'sess_abc123', domain: 'example.com', path: '/', httpOnly: true },
    { name: 'preferences', value: JSON.stringify({ theme: 'dark' }), domain: 'example.com', path: '/' }
  ]);
}"
```

---

## Local Storage

| Command | Example |
|---|---|
| List all | `playwright-cli localstorage-list` |
| Get value | `playwright-cli localstorage-get token` |
| Set value | `playwright-cli localstorage-set theme dark` |
| Set JSON | `playwright-cli localstorage-set user_settings '{"theme":"dark","language":"en"}'` |
| Delete item | `playwright-cli localstorage-delete token` |
| Clear all | `playwright-cli localstorage-clear` |

### Advanced: Multiple Operations
```bash
playwright-cli run-code "async page => {
  await page.evaluate(() => {
    localStorage.setItem('token', 'jwt_abc123');
    localStorage.setItem('user_id', '12345');
    localStorage.setItem('expires_at', Date.now() + 3600000);
  });
}"
```

---

## Session Storage

| Command | Example |
|---|---|
| List all | `playwright-cli sessionstorage-list` |
| Get value | `playwright-cli sessionstorage-get form_data` |
| Set value | `playwright-cli sessionstorage-set step 3` |
| Delete item | `playwright-cli sessionstorage-delete step` |
| Clear all | `playwright-cli sessionstorage-clear` |

---

## Common Patterns

```bash
playwright-cli open https://app.example.com/login
playwright-cli snapshot
playwright-cli fill e1 "user@example.com"
playwright-cli fill e2 "password123"
playwright-cli click e3
playwright-cli state-save auth.json

playwright-cli state-load auth.json
playwright-cli open https://app.example.com/dashboard
```

### Save and Restore Roundtrip
```bash
playwright-cli open https://example.com
playwright-cli eval "() => { document.cookie = 'session=abc123'; localStorage.setItem('user', 'john'); }"
playwright-cli state-save my-session.json

playwright-cli state-load my-session.json
playwright-cli open https://example.com
```

---

## Security Notes

- Never commit storage state files containing auth tokens
- Add `*.auth-state.json` to `.gitignore`
- Delete state files after automation completes
- Use environment variables for sensitive data
- By default, sessions run in-memory mode which is safer for sensitive operations
