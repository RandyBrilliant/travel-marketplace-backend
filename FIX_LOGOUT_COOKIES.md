# Logout Cookie Clearing Fix

## Problem

When logging out from the frontend, the cookies (`access_token`, `refresh_token`, and `csrftoken`) were not being removed from the browser.

## Root Cause

The logout endpoint was not properly clearing cookies because:

1. **Missing Parameters in `delete_cookie()`**: For browsers to properly delete a cookie, the deletion request must match ALL the parameters used when setting the cookie:
   - `path`
   - `domain`
   - `samesite`
   - `secure` (indirectly - affects how browsers handle the cookie)

2. **csrftoken Not Cleared**: The Django CSRF middleware sets a `csrftoken` cookie, but the logout endpoint wasn't clearing it.

### Before (INCORRECT)

```python
# Missing domain parameter and not clearing csrftoken
response.delete_cookie('access_token', path='/', samesite='Lax')
response.delete_cookie('refresh_token', path='/', samesite='Lax')
# csrftoken not cleared at all
```

### After (CORRECT)

```python
# All parameters match exactly how cookies were set
cookie_domain = None if settings.DEBUG else None
is_secure = not settings.DEBUG

response.delete_cookie(
    'access_token',
    path='/',
    domain=cookie_domain,  # ✅ Added
    samesite='Lax',
)

response.delete_cookie(
    'refresh_token',
    path='/',
    domain=cookie_domain,  # ✅ Added
    samesite='Lax',
)

response.delete_cookie(
    'csrftoken',  # ✅ Added
    path='/',
    domain=cookie_domain,
    samesite='Lax',
)

# Plus fallback method with set_cookie (belt and suspenders approach)
response.set_cookie(
    'access_token',
    value='',
    max_age=0,
    expires='Thu, 01 Jan 1970 00:00:00 GMT',  # ✅ Explicit expiry
    path='/',
    domain=cookie_domain,
    httponly=True,
    secure=is_secure,
    samesite='Lax',
)
# ... same for refresh_token and csrftoken
```

## What Changed

### 1. Added `domain` parameter to `delete_cookie()`
- Now matches the `domain=None` used when setting cookies
- Critical for proper cookie deletion

### 2. Clear all three cookies
- `access_token` ✅
- `refresh_token` ✅
- `csrftoken` ✅ (NEW)

### 3. Added explicit `expires` header
- Set to Unix epoch (Jan 1, 1970) to ensure cookie expiration
- Works as a fallback if `max_age=0` doesn't work in some browsers

### 4. Dual-method approach
- First try `delete_cookie()` (clean method)
- Then try `set_cookie()` with `max_age=0` and old expiry date (fallback)
- Ensures cookies are cleared even if parameters don't match exactly

## Cookie Parameters Explained

| Parameter | Login Value | Logout Value | Why It Must Match |
|-----------|-------------|--------------|-------------------|
| `path` | `/` | `/` | Browser checks path scope |
| `domain` | `None` | `None` | Browser checks domain scope |
| `samesite` | `Lax` | `Lax` | Part of cookie identity |
| `secure` | `True` (prod) | `True` (prod) | Affects cookie transmission |
| `httponly` | `True` | N/A in delete_cookie | Server-side only flag |

## How to Deploy the Fix

**On your server:**

```bash
cd /opt/travel-marketplace-backend
git pull
docker compose -f docker-compose.prod.yml restart api
```

## Testing

1. **Login to the frontend**:
   - Open browser DevTools → Application → Cookies
   - You should see: `access_token`, `refresh_token`, `csrftoken`

2. **Logout**:
   - Click logout in the frontend
   - Check cookies again

3. **Expected Result**:
   - ✅ All three cookies should be **removed**
   - ✅ No cookies with empty values should remain

4. **Verify in Network Tab**:
   - The logout response should have `Set-Cookie` headers with:
     - `Max-Age=0`
     - `Expires=Thu, 01 Jan 1970 00:00:00 GMT`

## Common Issues

### Cookies Still Not Clearing?

1. **Check domain mismatch**:
   - If cookies were set with a specific domain (e.g., `.goholiday.id`)
   - Logout must use the SAME domain
   - Check your CORS settings

2. **Check path mismatch**:
   - If cookies were set with path `/api/`
   - Logout must delete with path `/api/`
   - Our cookies use `/` (root)

3. **Browser cache**:
   - Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
   - Or clear all cookies manually

4. **HTTPS vs HTTP**:
   - Secure cookies (HTTPS) cannot be cleared by HTTP requests
   - Ensure your logout endpoint is called over HTTPS in production

## Related Files

- `travel-marketplace-backend/account/views.py` - LogoutView (fixed)
- `travel-marketplace-backend/account/token_views.py` - Login/refresh views (cookie setting)
- `travel-marketplace-frontend/stores/auth-store.ts` - Frontend logout logic
- `travel-marketplace-frontend/lib/api/auth.ts` - Logout API call

## Why This Matters

Proper logout is critical for:
- **Security**: Prevents session hijacking
- **User experience**: Users expect logout to clear all credentials
- **Compliance**: Many security standards require proper logout
- **Privacy**: Cookies may contain sensitive information

