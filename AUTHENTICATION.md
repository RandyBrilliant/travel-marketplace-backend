# Authentication Guide

This project uses JWT (JSON Web Token) authentication via `djangorestframework-simplejwt` with a custom token serializer that includes user information in the JWT payload.

## Token Endpoints

### 1. Obtain Access and Refresh Tokens

**Endpoint:** `POST /api/token/`

**Description:** Authenticate with email and password to receive both access and refresh tokens. The JWT access token payload includes user information (email, role, full_name, profile_picture_url) for convenience.

**Request:**
```bash
POST /api/token/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Note:** The response only contains tokens. User information is embedded in the JWT access token payload itself. Decode the access token to get:
- `email`: User's email address
- `role`: User role (SUPPLIER, RESELLER, STAFF, CUSTOMER)
- `full_name`: Full name from profile (company_name for suppliers, display_name for resellers, name for staff, email fallback)
- `profile_picture_url`: Absolute URL to profile picture (if available)

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "your_password"
  }'
```

**Python Example:**
```python
import requests

response = requests.post(
    'http://localhost:8000/api/token/',
    json={
        'email': 'admin@example.com',
        'password': 'your_password'
    }
)

tokens = response.json()
access_token = tokens['access']
refresh_token = tokens['refresh']

print(f"Access Token: {access_token}")
print(f"Refresh Token: {refresh_token}")
```

**JavaScript/Fetch Example:**
```javascript
const response = await fetch('http://localhost:8000/api/token/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'admin@example.com',
    password: 'your_password'
  })
});

const tokens = await response.json();
const accessToken = tokens.access;
const refreshToken = tokens.refresh;

console.log('Access Token:', accessToken);
console.log('Refresh Token:', refreshToken);
```

---

### 2. Refresh Access Token

**Endpoint:** `POST /api/token/refresh/`

**Description:** Use a refresh token to obtain a new access token. The refresh token may also be rotated (new refresh token returned) depending on configuration.

**Request:**
```bash
POST /api/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Note:** With `ROTATE_REFRESH_TOKENS: True` configured, the response may also include a new refresh token:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "your_refresh_token_here"
  }'
```

**Python Example:**
```python
import requests

response = requests.post(
    'http://localhost:8000/api/token/refresh/',
    json={
        'refresh': 'your_refresh_token_here'
    }
)

tokens = response.json()
new_access_token = tokens['access']

# If refresh token rotation is enabled, you may also get a new refresh token
if 'refresh' in tokens:
    new_refresh_token = tokens['refresh']
    print(f"New Refresh Token: {new_refresh_token}")

print(f"New Access Token: {new_access_token}")
```

**JavaScript/Fetch Example:**
```javascript
const response = await fetch('http://localhost:8000/api/token/refresh/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    refresh: 'your_refresh_token_here'
  })
});

const tokens = await response.json();
const newAccessToken = tokens.access;

// If refresh token rotation is enabled
if (tokens.refresh) {
  const newRefreshToken = tokens.refresh;
  console.log('New Refresh Token:', newRefreshToken);
}

console.log('New Access Token:', newAccessToken);
```

---

## JWT Token Payload

The access token includes user information in its payload. You can decode the JWT token to access:

- `email`: User's email address
- `role`: User role (`SUPPLIER`, `RESELLER`, `STAFF`, `CUSTOMER`)
- `full_name`: Full name from profile:
  - Suppliers: `company_name`
  - Resellers: `display_name`
  - Staff: `name`
  - Fallback: `email` if no profile exists
- `profile_picture_url`: Absolute URL to profile picture (if available)

**Decoding JWT Token (JavaScript):**
```javascript
// Using jwt-decode library
import jwt_decode from 'jwt-decode';

const decoded = jwt_decode(accessToken);
console.log('User email:', decoded.email);
console.log('User role:', decoded.role);
console.log('Full name:', decoded.full_name);
console.log('Profile picture:', decoded.profile_picture_url);
```

**Decoding JWT Token (Python):**
```python
import jwt

# Decode without verification (for reading payload only)
decoded = jwt.decode(access_token, options={"verify_signature": False})
print(f"User email: {decoded['email']}")
print(f"User role: {decoded['role']}")
print(f"Full name: {decoded['full_name']}")
print(f"Profile picture: {decoded.get('profile_picture_url')}")
```

**Note:** The token payload is base64 encoded and can be decoded without the secret key. However, always verify the token signature on the server side before trusting the payload.

---

## Using Tokens in API Requests

Once you have an access token, include it in the `Authorization` header for authenticated requests:

**Header Format:**
```
Authorization: Bearer <access_token>
```

**cURL Example:**
```bash
curl -X GET http://localhost:8000/users/ \
  -H "Authorization: Bearer your_access_token_here"
```

**Python Example:**
```python
import requests

headers = {
    'Authorization': f'Bearer {access_token}'
}

response = requests.get('http://localhost:8000/users/', headers=headers)
data = response.json()
```

**JavaScript/Fetch Example:**
```javascript
const response = await fetch('http://localhost:8000/users/', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});

const data = await response.json();
```

---

## Token Configuration

Token lifetimes are configured in `backend/settings.py`:

- **Access Token Lifetime:** Default 5 minutes (configurable via `ACCESS_TOKEN_LIFETIME_MINUTES` environment variable)
- **Refresh Token Lifetime:** Default 7 days (configurable via `REFRESH_TOKEN_LIFETIME_DAYS` environment variable)
- **Refresh Token Rotation:** Enabled (`ROTATE_REFRESH_TOKENS: True`)
- **Blacklist After Rotation:** Enabled (`BLACKLIST_AFTER_ROTATION: True`)

### Environment Variables

You can configure token lifetimes in your `.env` file:

```env
ACCESS_TOKEN_LIFETIME_MINUTES=5
REFRESH_TOKEN_LIFETIME_DAYS=7
```

---

## Complete Authentication Flow Example

### Step 1: Login and Get Tokens
```python
import requests

# Login
login_response = requests.post(
    'http://localhost:8000/api/token/',
    json={
        'email': 'admin@example.com',
        'password': 'your_password'
    }
)

tokens = login_response.json()
access_token = tokens['access']
refresh_token = tokens['refresh']

# Store these tokens securely (e.g., in localStorage, secure cookie, or keychain)
```

### Step 2: Use Access Token for API Calls
```python
# Make authenticated API call
headers = {
    'Authorization': f'Bearer {access_token}'
}

response = requests.get('http://localhost:8000/users/', headers=headers)

if response.status_code == 401:
    # Access token expired, need to refresh
    pass
```

### Step 3: Refresh Access Token When Expired
```python
# When access token expires (401 Unauthorized), refresh it
refresh_response = requests.post(
    'http://localhost:8000/api/token/refresh/',
    json={
        'refresh': refresh_token
    }
)

if refresh_response.status_code == 200:
    new_tokens = refresh_response.json()
    access_token = new_tokens['access']
    
    # If refresh token rotation is enabled, update refresh token too
    if 'refresh' in new_tokens:
        refresh_token = new_tokens['refresh']
    
    # Retry the original request with new access token
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get('http://localhost:8000/users/', headers=headers)
```

---

## Error Responses

### 401 Unauthorized (Invalid Credentials)
```json
{
  "detail": "No active account found with the given credentials"
}
```

### 401 Unauthorized (Invalid/Expired Token)
```json
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid"
}
```

### 401 Unauthorized (Expired Refresh Token)
```json
{
  "detail": "Token is invalid or expired",
  "code": "token_not_valid"
}
```

---

## Best Practices

1. **Store Tokens Securely:**
   - Never store tokens in localStorage for production (XSS vulnerability)
   - Use httpOnly cookies or secure storage mechanisms
   - Consider using secure keychain/keystore on mobile apps

2. **Handle Token Expiration:**
   - Implement automatic token refresh before expiration
   - Handle 401 responses by refreshing the token and retrying the request

3. **Refresh Token Rotation:**
   - With rotation enabled, always use the new refresh token after refreshing
   - Old refresh tokens are blacklisted and cannot be reused

4. **Token Lifetime:**
   - Access tokens are short-lived (default 5 minutes) for security
   - Refresh tokens are longer-lived (default 7 days) for user convenience
   - Adjust lifetimes based on your security requirements

5. **Logout:**
   - To "logout", simply discard the tokens on the client side
   - If using token blacklisting, you may want to implement a logout endpoint that blacklists the current refresh token

---

## Testing Authentication

### Using cURL

**1. Get tokens:**
```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "password123"}'
```

**2. Use access token:**
```bash
curl -X GET http://localhost:8000/users/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**3. Refresh token:**
```bash
curl -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "YOUR_REFRESH_TOKEN"}'
```

### Using Python Requests

```python
import requests

BASE_URL = 'http://localhost:8000'

# Step 1: Login
response = requests.post(
    f'{BASE_URL}/api/token/',
    json={'email': 'admin@example.com', 'password': 'password123'}
)
tokens = response.json()
access_token = tokens['access']
refresh_token = tokens['refresh']

# Step 2: Make authenticated request
headers = {'Authorization': f'Bearer {access_token}'}
response = requests.get(f'{BASE_URL}/users/', headers=headers)
print(response.json())

# Step 3: Refresh when needed
response = requests.post(
    f'{BASE_URL}/api/token/refresh/',
    json={'refresh': refresh_token}
)
new_tokens = response.json()
access_token = new_tokens['access']
```

---

## Summary

1. **Get Tokens:** POST to `/api/token/` with email and password - you'll receive both `access` and `refresh` tokens in the response.

2. **JWT Payload:** The access token contains user information (email, role, full_name, profile_picture_url) in its payload - decode it to access user info without additional API calls.

3. **Use Refresh Token:** POST to `/api/token/refresh/` with the refresh token to get a new access token.

4. **Use Access Token:** Include `Authorization: Bearer <access_token>` header in all authenticated API requests.

5. **Token Lifetimes:**
   - Access token: 5 minutes (default)
   - Refresh token: 7 days (default)

6. **Token Rotation:** Enabled - old refresh tokens are blacklisted after use for security.

