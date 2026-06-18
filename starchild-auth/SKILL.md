---
name: starchild-auth
version: 1.3.0
description: |
  Starchild Auth SDK: add OAuth login to any web app with one SDK.

  Use when integrating Starchild login into a project (e.g. add Starchild sign-in to my React app, set up OAuth with iamstarchild.com, implement login/logout with Starchild Auth SDK).
author: starchild
tags: [auth, oauth, login, sdk, react, vue, html]
metadata:
  starchild:
    emoji: "\U0001F511"
    skillKey: starchild-auth
---

# 🔑 Starchild Auth SDK

Integrate Starchild OAuth login into any web application — React, Vue, or plain HTML. The SDK handles the full OAuth popup flow, token management, automatic refresh, and session restoration.

## When to Use

- Adding Starchild login to a web project
- Implementing OAuth authentication with iamstarchild.com
- Building a third-party app that needs Starchild user identity
- Replacing a custom auth flow with Starchild SSO

---

## Step 1 — Register Your App & Get Client ID

1. Go to **[iamstarchild.com](https://iamstarchild.com)** → click the **More** menu (left sidebar) → **OAuth Apps**
   - Direct link: `https://iamstarchild.com/oauth-apps`
2. Click **Create App**
3. Fill in:
   - **App Name** *(required)*: your application name
   - **Allowed Origin** *(required)*: the origin of your website (e.g. `https://your-app.com`). For local development, use `http://localhost:3000`. Must be a valid origin — no paths, query params, or hash allowed. Non-localhost origins must use `https://`.
   - **Description** *(optional)*: only visible to you
4. After creation, a dialog will show your **Client ID** — copy it immediately

> ⚠️ Keep your Client ID safe. Never commit it directly in source code — use environment variables.
> Each user can create up to **10** OAuth apps.

---

## Step 2 — Install the SDK

### npm / yarn / pnpm

```bash
# npm
npm install starchild-auth-sdk

# yarn
yarn add starchild-auth-sdk

# pnpm
pnpm add starchild-auth-sdk
```

### CDN (for plain HTML)

The SDK provides **two builds**. For plain `<script>` tags, use the **UMD** build:

```html
<!-- unpkg (recommended) -->
<script src="https://unpkg.com/starchild-auth-sdk/dist/starchild-auth.umd.cjs"></script>

<!-- npmmirror (alternative, for China mainland) -->
<script src="https://registry.npmmirror.com/starchild-auth-sdk/latest/files/dist/starchild-auth.umd.cjs"></script>
```

> ⚠️ **Do NOT use** `starchild-auth.js` with a plain `<script>` tag — that file is an ES Module and will fail silently. Use `starchild-auth.umd.cjs` for `<script>` tags, or use `<script type="module">` with the ESM build (see examples below).

> 💡 **CDN 加载失败？** 如果两个 CDN 都无法访问（如在受限网络环境中），可以用 `curl` 下载到本地后通过相对路径引用：
> ```bash
> curl -sL "https://unpkg.com/starchild-auth-sdk/dist/starchild-auth.umd.cjs" -o starchild-auth.umd.cjs
> ```
> 然后 `<script src="starchild-auth.umd.cjs"></script>`

When loaded via UMD CDN, the class is available directly as `window.StarchildAuth` (it's the constructor itself, not a namespace object).

---

## Step 3 — Initialize the SDK

```typescript
import { StarchildAuth } from 'starchild-auth-sdk'

const auth = new StarchildAuth({
  clientId: 'your-client-id',

  // Called after successful login (popup or auto-login session restore)
  onLogin: ({ accessToken, refreshToken, expiresIn, userInfo }) => {
    console.log('Logged in:', userInfo.agentName)
    console.log('Avatar:', userInfo.agentAvatar)
  },

  // Called after logout
  onLogout: () => {
    console.log('Logged out')
  },

  // Token auto-refreshes every 12 minutes
  onTokenRefresh: (newAccessToken) => {
    console.log('Token refreshed')
  },

  // Called when refresh fails (session expired)
  onTokenRefreshFailed: () => {
    console.log('Session expired, please log in again')
  },
})
```

> **Auto-login**: By default (`autoLogin: true`), the SDK checks localStorage for a stored refresh token on initialization and automatically restores the session. This means `onLogin` may fire immediately after construction without calling `login()`.

---

## Step 4 — Login / Logout / Status

```typescript
// Trigger login (opens Starchild OAuth popup)
const { accessToken, refreshToken, expiresIn, userInfo } = await auth.login()

// Logout (clears tokens, revokes refresh token via API)
await auth.logout()

// Check login status
const isLoggedIn: boolean = auth.isLoggedIn()

// Get current access token (null if not logged in)
const token: string | null = auth.getToken()

// Get current user info (null if not logged in)
const user: UserInfo | null = auth.getUserInfo()
// user = { userInfoId: string, agentName: string, agentAvatar: string }

// Manually trigger token refresh (normally automatic every 12 min)
const newToken: string = await auth.refreshToken()

// Destroy instance (remove listeners, clear timers, clear tokens)
auth.destroy()
```

---

## Framework Examples

### React

```tsx
// src/hooks/useStarchildAuth.ts
import { useState, useEffect, useRef, useCallback } from 'react'
import { StarchildAuth } from 'starchild-auth-sdk'
import type { UserInfo, LoginResult } from 'starchild-auth-sdk'

export function useStarchildAuth() {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const authRef = useRef<StarchildAuth | null>(null)

  useEffect(() => {
    const auth = new StarchildAuth({
      clientId: import.meta.env.VITE_STARCHILD_CLIENT_ID,
      onLogin: ({ accessToken, userInfo }: LoginResult) => {
        setUser(userInfo)
        setToken(accessToken)
        setLoading(false)
      },
      onLogout: () => {
        setUser(null)
        setToken(null)
      },
      onTokenRefresh: (newToken: string) => {
        setToken(newToken)
      },
      onTokenRefreshFailed: () => {
        setUser(null)
        setToken(null)
      },
      // autoLogin: true (default) — will restore session from localStorage
    })

    authRef.current = auth

    // If auto-login doesn't fire onLogin (no stored session), stop loading
    const timeout = setTimeout(() => setLoading(false), 1500)

    return () => {
      clearTimeout(timeout)
      auth.destroy()
    }
  }, [])

  const login = useCallback(async () => {
    if (!authRef.current) return
    return await authRef.current.login()
  }, [])

  const logout = useCallback(async () => {
    if (!authRef.current) return
    await authRef.current.logout()
  }, [])

  return { user, token, loading, login, logout, isLoggedIn: !!user }
}
```

```tsx
// src/App.tsx
import { useStarchildAuth } from './hooks/useStarchildAuth'

function App() {
  const { user, loading, login, logout, isLoggedIn } = useStarchildAuth()

  if (loading) return <div>Loading...</div>

  return (
    <div>
      {isLoggedIn ? (
        <div>
          <p>Welcome, {user?.agentName}</p>
          <img src={user?.agentAvatar} alt="avatar" width={40} />
          <button onClick={logout}>Logout</button>
        </div>
      ) : (
        <button onClick={login}>Login with Starchild</button>
      )}
    </div>
  )
}

export default App
```

### Vue 3 (Composition API)

```typescript
// src/composables/useStarchildAuth.ts
import { ref, onMounted, onUnmounted } from 'vue'
import { StarchildAuth } from 'starchild-auth-sdk'
import type { UserInfo, LoginResult } from 'starchild-auth-sdk'

export function useStarchildAuth() {
  const user = ref<UserInfo | null>(null)
  const token = ref<string | null>(null)
  const loading = ref(true)
  let authInstance: StarchildAuth | null = null

  onMounted(() => {
    authInstance = new StarchildAuth({
      clientId: import.meta.env.VITE_STARCHILD_CLIENT_ID,
      onLogin: ({ accessToken, userInfo }: LoginResult) => {
        user.value = userInfo
        token.value = accessToken
        loading.value = false
      },
      onLogout: () => {
        user.value = null
        token.value = null
      },
      onTokenRefresh: (newToken: string) => {
        token.value = newToken
      },
      onTokenRefreshFailed: () => {
        user.value = null
        token.value = null
      },
    })

    // If no stored session, stop loading after timeout
    setTimeout(() => { loading.value = false }, 1500)
  })

  onUnmounted(() => {
    authInstance?.destroy()
  })

  const login = async () => {
    if (!authInstance) return
    return await authInstance.login()
  }

  const logout = async () => {
    if (!authInstance) return
    await authInstance.logout()
  }

  const isLoggedIn = () => !!user.value

  return { user, token, loading, login, logout, isLoggedIn }
}
```

```vue
<!-- src/App.vue -->
<template>
  <div v-if="loading">Loading...</div>
  <div v-else-if="user">
    <p>Welcome, {{ user.agentName }}</p>
    <img :src="user.agentAvatar" alt="avatar" width="40" />
    <button @click="logout">Logout</button>
  </div>
  <div v-else>
    <button @click="login">Login with Starchild</button>
  </div>
</template>

<script setup lang="ts">
import { useStarchildAuth } from './composables/useStarchildAuth'

const { user, loading, login, logout } = useStarchildAuth()
</script>
```

### Plain HTML — UMD (recommended for `<script>` tags)

> 💡 如果 CDN 加载失败，参考上方 Step 2 中的 CDN 备选源和本地下载方案。

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Starchild Auth Demo</title>
  <!-- UMD build: works with plain <script> tags -->
  <!-- If CDN is blocked, download the file locally and use a relative path instead -->
  <script src="https://unpkg.com/starchild-auth-sdk/dist/starchild-auth.umd.cjs"></script>
</head>
<body>
  <div id="app">
    <div id="logged-out">
      <button id="login-btn">Login with Starchild</button>
    </div>
    <div id="logged-in" style="display: none">
      <p>Welcome, <span id="user-name"></span></p>
      <img id="user-avatar" width="40" />
      <button id="logout-btn">Logout</button>
    </div>
  </div>

  <script>
    // UMD exposes: window.StarchildAuth (object) → .StarchildAuth (constructor)
    // window.StarchildAuth is the constructor itself (not a namespace object)
    if (typeof window.StarchildAuth !== 'function') {
      document.getElementById('logged-out').innerHTML =
        '<p style="color:red">SDK failed to load. Check if the CDN script loaded correctly.</p>'
      throw new Error('StarchildAuth SDK not loaded')
    }

    var auth = new StarchildAuth({
      clientId: 'your-client-id',
      onLogin: function (result) {
        showLoggedIn(result.userInfo)
      },
      onLogout: function () {
        showLoggedOut()
      },
      onTokenRefresh: function (newToken) {
        console.log('Token refreshed')
      },
      onTokenRefreshFailed: function () {
        showLoggedOut()
      },
      // autoLogin: true (default) — restores session automatically
    })

    document.getElementById('login-btn').addEventListener('click', async function () {
      try {
        await auth.login()
      } catch (err) {
        console.error('Login failed:', err.message)
      }
    })

    document.getElementById('logout-btn').addEventListener('click', async function () {
      await auth.logout()
    })

    function showLoggedIn(user) {
      document.getElementById('logged-out').style.display = 'none'
      document.getElementById('logged-in').style.display = 'block'
      document.getElementById('user-name').textContent = user.agentName
      if (user.agentAvatar) {
        document.getElementById('user-avatar').src = user.agentAvatar
      }
    }

    function showLoggedOut() {
      document.getElementById('logged-out').style.display = 'block'
      document.getElementById('logged-in').style.display = 'none'
    }
  </script>
</body>
</html>
```

### Plain HTML — ES Module (alternative)

If you prefer ES Module syntax, use `<script type="module">`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Starchild Auth Demo (ESM)</title>
</head>
<body>
  <button id="login-btn">Login with Starchild</button>
  <div id="logged-in" style="display: none">
    <p>Welcome, <span id="user-name"></span></p>
    <button id="logout-btn">Logout</button>
  </div>

  <script type="module">
    import { StarchildAuth } from 'https://unpkg.com/starchild-auth-sdk/dist/starchild-auth.js'

    const auth = new StarchildAuth({
      clientId: 'your-client-id',
      onLogin: ({ userInfo }) => {
        document.getElementById('login-btn').style.display = 'none'
        document.getElementById('logged-in').style.display = 'block'
        document.getElementById('user-name').textContent = userInfo.agentName
      },
      onLogout: () => {
        document.getElementById('login-btn').style.display = 'block'
        document.getElementById('logged-in').style.display = 'none'
      },
    })

    document.getElementById('login-btn').addEventListener('click', () => auth.login())
    document.getElementById('logout-btn').addEventListener('click', () => auth.logout())
  </script>
</body>
</html>
```

---

## API Reference

### `StarchildAuthOptions` (Constructor Options)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `clientId` | `string` | *(required)* | OAuth Client ID from iamstarchild.com |
| `onLogin` | `(result: LoginResult) => void` | — | Called after successful login (popup or auto-login) |
| `onLogout` | `() => void` | — | Called after logout |
| `onTokenRefresh` | `(accessToken: string) => void` | — | Called when token is auto-refreshed |
| `onTokenRefreshFailed` | `() => void` | — | Called when token refresh fails (session expired) |
| `autoLogin` | `boolean` | `true` | Attempt to restore session from localStorage on init |
| `origin` | `string` | `'https://iamstarchild.com'` | Starchild origin URL (for popup login page) |
| `apiBase` | `string` | `'https://go-api.iamstarchild.com/v1'` | Go API base URL (for token refresh & logout) |
| `chatApiBase` | `string` | `'https://ai-api.iamstarchild.com'` | AI API base URL (for `/v1/oauth/userinfo`) |
| `popupWidth` | `number` | `480` | Login popup width in pixels |
| `popupHeight` | `number` | `640` | Login popup height in pixels |
| `refreshInterval` | `number` | `720000` | Auto-refresh interval in ms (default: 12 minutes) |

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `login()` | `Promise<LoginResult>` | Opens OAuth popup and returns credentials on success |
| `logout()` | `Promise<void>` | Clears session, revokes refresh token via API |
| `isLoggedIn()` | `boolean` | Whether user is currently authenticated |
| `getToken()` | `string \| null` | Current access token, or `null` |
| `getUserInfo()` | `UserInfo \| null` | Current user info, or `null` |
| `refreshToken()` | `Promise<string>` | Manually trigger token refresh, returns new access token |
| `destroy()` | `void` | Remove listeners, clear timers, clear tokens. Instance cannot be reused. |

### `LoginResult` Type

```typescript
interface LoginResult {
  accessToken: string
  refreshToken: string
  expiresIn: number
  userInfo: UserInfo
}
```

### `UserInfo` Type

```typescript
interface UserInfo {
  /** Unique user ID */
  userInfoId: string
  /** Display name (agent name) */
  agentName: string
  /** Avatar URL */
  agentAvatar: string
}
```

### Token Lifecycle

- Access tokens are **short-lived** and auto-refresh every **12 minutes** (configurable via `refreshInterval`)
- The SDK stores the **refresh token** in `localStorage` (key: `starchild_rt_{clientId}`)
- On page reload, if `autoLogin` is `true` (default), the SDK uses the stored refresh token to restore the session automatically — `onLogin` fires again with fresh tokens
- When the page returns from background (visibility change), the SDK automatically refreshes the token
- If refresh fails (e.g. user revoked access, token expired), `onTokenRefreshFailed` fires and the stored refresh token is cleared

---

## Sending Authenticated API Requests

Once logged in, include the access token in your API requests:

```typescript
const response = await fetch('https://api.your-app.com/data', {
  headers: {
    Authorization: `Bearer ${auth.getToken()}`,
  },
})
```

For React / Vue, use the `token` from the hook/composable:

```typescript
// React example
const { token } = useStarchildAuth()

const fetchData = async () => {
  const res = await fetch('/api/data', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return res.json()
}
```

---

## Important Notes

### CDN Build Selection

| Build | File | Usage |
|-------|------|-------|
| **UMD** | `starchild-auth.umd.cjs` | `<script>` tags — exposes `window.StarchildAuth` (constructor) |
| **ESM** | `starchild-auth.js` | `<script type="module">` or bundlers (Vite, webpack, etc.) |

> **Common mistake**: Using `starchild-auth.js` with a plain `<script>` tag. This will fail silently because the ESM file uses `export` syntax which is invalid in non-module scripts. Always use the `.umd.cjs` build for plain `<script>` tags.

### Session Persistence

The SDK stores the refresh token in `localStorage` under the key `starchild_rt_{clientId}`. This enables:
- **Auto-login on page reload** — no need to call `login()` again
- **Cross-tab session sharing** — all tabs with the same `clientId` share the session

To fully clear a user's session, call `auth.logout()` which removes the stored token and revokes it server-side.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Popup blocked | Ensure `login()` is called from a user gesture (click handler). Browsers block popups not triggered by user interaction. |
| Origin mismatch | Verify the **Allowed Origin** in OAuth Apps settings matches your site's origin exactly (e.g. `https://your-app.com`). No trailing slash, no path. |
| `StarchildAuth is not defined` (CDN) | You're using the ESM build (`starchild-auth.js`) with a plain `<script>` tag. Switch to the UMD build (`starchild-auth.umd.cjs`), or use `<script type="module">` with `import`. |
| Token refresh failing | Check that the app hasn't been revoked in user's Starchild settings. Also check browser console for network errors. |
| `onLogin` fires on page load | This is expected behavior — `autoLogin: true` (default) restores the session from localStorage. Set `autoLogin: false` to disable. |
| CDN blocked | unpkg.com may be slow/blocked in some environments. Use `npmmirror` as alternative (`https://registry.npmmirror.com/starchild-auth-sdk/latest/files/dist/starchild-auth.umd.cjs`), or download the SDK file locally and serve it from your own domain. |
