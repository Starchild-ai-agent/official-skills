---
name: starchild-auth
version: 1.0.0
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

Integrate Starchild OAuth login into any web application — React, Vue, or plain HTML. The SDK handles the full OAuth flow, token management, and automatic refresh.

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

```html
<script src="https://cdn.jsdelivr.net/npm/starchild-auth-sdk/dist/starchild-auth.js"></script>
```

When loaded via CDN, the SDK is available as `window.StarchildAuth`.

---

## Step 3 — Initialize the SDK

```typescript
import { StarchildAuth } from 'starchild-auth-sdk'

const auth = new StarchildAuth({
  clientId: 'your-client-id',

  // Called after successful login
  onLogin: ({ accessToken, userInfo }) => {
    console.log('Logged in:', userInfo.agentName)
  },

  // Called after logout
  onLogout: () => {
    console.log('Logged out')
  },

  // Token auto-refreshes every 12 minutes
  onTokenRefresh: (newToken) => {
    console.log('Token refreshed')
  },

  // Called when refresh fails (session expired)
  onTokenRefreshFailed: () => {
    console.log('Session expired, please log in again')
  },
})
```

---

## Step 4 — Login / Logout / Status

```typescript
// Trigger login (opens Starchild OAuth popup)
const { accessToken, userInfo } = await auth.login()

// Logout (clears tokens and session)
await auth.logout()

// Check login status
const isLoggedIn: boolean = auth.isLoggedIn()

// Get current access token (null if not logged in)
const token: string | null = auth.getToken()

// Get current user info (null if not logged in)
const user: UserInfo | null = auth.getUserInfo()
```

---

## Framework Examples

### React

```tsx
// src/hooks/useStarchildAuth.ts
import { useState, useEffect, useRef } from 'react'
import { StarchildAuth, UserInfo } from 'starchild-auth-sdk'

export function useStarchildAuth() {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const authRef = useRef<StarchildAuth | null>(null)

  useEffect(() => {
    const auth = new StarchildAuth({
      clientId: import.meta.env.VITE_STARCHILD_CLIENT_ID,
      onLogin: ({ accessToken, userInfo }) => {
        setUser(userInfo)
        setToken(accessToken)
      },
      onLogout: () => {
        setUser(null)
        setToken(null)
      },
      onTokenRefresh: (newToken) => {
        setToken(newToken)
      },
      onTokenRefreshFailed: () => {
        setUser(null)
        setToken(null)
      },
    })

    authRef.current = auth

    // Restore session if token exists
    if (auth.isLoggedIn()) {
      setUser(auth.getUserInfo())
      setToken(auth.getToken())
    }
    setLoading(false)

    return () => {
      // Cleanup if needed
    }
  }, [])

  const login = async () => {
    if (!authRef.current) return
    const result = await authRef.current.login()
    return result
  }

  const logout = async () => {
    if (!authRef.current) return
    await authRef.current.logout()
  }

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
          <img src={user?.avatar} alt="avatar" width={40} />
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

```vue
<!-- src/composables/useStarchildAuth.ts -->
<script setup lang="ts">
// composable file: src/composables/useStarchildAuth.ts
</script>
```

```typescript
// src/composables/useStarchildAuth.ts
import { ref, onMounted } from 'vue'
import { StarchildAuth, UserInfo } from 'starchild-auth-sdk'

export function useStarchildAuth() {
  const user = ref<UserInfo | null>(null)
  const token = ref<string | null>(null)
  const loading = ref(true)
  let authInstance: StarchildAuth | null = null

  onMounted(() => {
    authInstance = new StarchildAuth({
      clientId: import.meta.env.VITE_STARCHILD_CLIENT_ID,
      onLogin: ({ accessToken, userInfo }) => {
        user.value = userInfo
        token.value = accessToken
      },
      onLogout: () => {
        user.value = null
        token.value = null
      },
      onTokenRefresh: (newToken) => {
        token.value = newToken
      },
      onTokenRefreshFailed: () => {
        user.value = null
        token.value = null
      },
    })

    if (authInstance.isLoggedIn()) {
      user.value = authInstance.getUserInfo()
      token.value = authInstance.getToken()
    }
    loading.value = false
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
    <img :src="user.avatar" alt="avatar" width="40" />
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

### Plain HTML (CDN)

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Starchild Auth Demo</title>
  <script src="https://cdn.jsdelivr.net/npm/starchild-auth-sdk/dist/starchild-auth.js"></script>
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
    const auth = new StarchildAuth({
      clientId: 'your-client-id',
      onLogin: ({ accessToken, userInfo }) => {
        showLoggedIn(userInfo)
      },
      onLogout: () => {
        showLoggedOut()
      },
      onTokenRefresh: (newToken) => {
        console.log('Token refreshed')
      },
      onTokenRefreshFailed: () => {
        showLoggedOut()
      },
    })

    // Restore session on page load
    if (auth.isLoggedIn()) {
      showLoggedIn(auth.getUserInfo())
    }

    document.getElementById('login-btn').addEventListener('click', async () => {
      try {
        await auth.login()
      } catch (err) {
        console.error('Login failed:', err)
      }
    })

    document.getElementById('logout-btn').addEventListener('click', async () => {
      await auth.logout()
    })

    function showLoggedIn(user) {
      document.getElementById('logged-out').style.display = 'none'
      document.getElementById('logged-in').style.display = 'block'
      document.getElementById('user-name').textContent = user.agentName
      document.getElementById('user-avatar').src = user.avatar
    }

    function showLoggedOut() {
      document.getElementById('logged-out').style.display = 'block'
      document.getElementById('logged-in').style.display = 'none'
    }
  </script>
</body>
</html>
```

---

## API Reference

### `StarchildAuth` Constructor Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `clientId` | `string` | ✅ | OAuth Client ID from iamstarchild.com |
| `onLogin` | `(data: { accessToken: string; userInfo: UserInfo }) => void` | — | Called after successful login |
| `onLogout` | `() => void` | — | Called after logout |
| `onTokenRefresh` | `(newToken: string) => void` | — | Called when token is auto-refreshed |
| `onTokenRefreshFailed` | `() => void` | — | Called when token refresh fails (session expired) |

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `login()` | `Promise<{ accessToken: string; userInfo: UserInfo }>` | Opens OAuth popup and returns credentials |
| `logout()` | `Promise<void>` | Clears session and tokens |
| `isLoggedIn()` | `boolean` | Whether user is currently authenticated |
| `getToken()` | `string \| null` | Current access token, or `null` |
| `getUserInfo()` | `UserInfo \| null` | Current user info, or `null` |

### `UserInfo` Type

```typescript
interface UserInfo {
  /** Unique user ID */
  id: string
  /** Display name (agent name) */
  agentName: string
  /** Avatar URL */
  avatar: string
  /** Email address (if authorized) */
  email?: string
}
```

### Token Lifecycle

- Access tokens are **short-lived** and auto-refresh every **12 minutes**
- The SDK handles refresh transparently — no manual intervention needed
- If refresh fails (e.g. user revoked access), `onTokenRefreshFailed` fires
- On page reload, the SDK restores the session from stored tokens automatically

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

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Popup blocked | Ensure `login()` is called from a user gesture (click handler) |
| Origin mismatch | Verify the **Allowed Origin** in OAuth Apps settings matches your site's origin exactly (e.g. `https://your-app.com`) |
| Token refresh failing | Check that the app hasn't been revoked in user's Starchild settings |
| CDN script not loading | Verify network access to `cdn.jsdelivr.net`; consider using npm instead |
| `StarchildAuth is not defined` (CDN) | Ensure the `<script>` tag loads before your code |
