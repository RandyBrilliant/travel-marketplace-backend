# My Profile Endpoints

Endpoints for users to view and manage their own profile information.

## Overview

These endpoints allow authenticated users to access and manage their own profile data. The endpoint you use depends on your user role.

---

## Supplier Profile

### Get My Supplier Profile

**Endpoint:** `GET /suppliers/me/profile/`

**Permission:** Authenticated user with `SUPPLIER` role

**Description:** Returns the authenticated supplier's own profile.

**Request:**
```bash
GET /suppliers/me/profile/
Authorization: Bearer <your_access_token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "user": 123,
  "company_name": "Travel Co",
  "contact_person": "John Doe",
  "contact_phone": "+1234567890",
  "address": "123 Main St, City, Country",
  "tax_id": "TAX123456",
  "status": "ACTIVE",
  "photo": "http://localhost:8000/media/profile_photos/suppliers/photo.jpg",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Response (404 Not Found):** If profile doesn't exist
```json
{
  "detail": "Not found."
}
```

**Response (403 Forbidden):** If user doesn't have SUPPLIER role
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**Field Descriptions:**
- `id` (read-only): Profile ID
- `user` (read-only): User ID (automatically set to authenticated user)
- `company_name` (required): Official company/business name
- `contact_person` (required): Primary contact person name
- `contact_phone` (required): Primary contact phone number
- `address` (optional): Business address
- `tax_id` (optional): Tax identification number
- `status` (optional): Status - `PENDING`, `ACTIVE`, or `SUSPENDED`
- `photo` (optional): Profile photo URL (absolute URL if photo is uploaded)
- `created_at` (read-only): Profile creation timestamp
- `updated_at` (read-only): Last update timestamp

**cURL Example:**
```bash
curl -X GET http://localhost:8000/suppliers/me/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Python Example:**
```python
import requests

headers = {
    'Authorization': f'Bearer {access_token}'
}

response = requests.get('http://localhost:8000/suppliers/me/profile/', headers=headers)
profile = response.json()
print(profile)
```

**JavaScript/Fetch Example:**
```javascript
const response = await fetch('http://localhost:8000/suppliers/me/profile/', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});

const profile = await response.json();
console.log(profile);
```

---

## Reseller Profile

### Get My Reseller Profile

**Endpoint:** `GET /resellers/me/profile/`

**Permission:** Authenticated user with `RESELLER` role

**Description:** Returns the authenticated reseller's own profile.

**Request:**
```bash
GET /resellers/me/profile/
Authorization: Bearer <your_access_token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "user": 456,
  "display_name": "My Travel Agency",
  "contact_phone": "+1234567890",
  "address": "456 Business Ave",
  "referral_code": "ABC12345",
  "sponsor": 2,
  "group_root": 2,
  "own_commission_rate": "15.00",
  "upline_commission_rate": "5.00",
  "status": "ACTIVE",
  "bank_name": "Bank Name",
  "bank_account_name": "Account Holder",
  "bank_account_number": "1234567890",
  "direct_downline_count": 5,
  "photo": "http://localhost:8000/media/profile_photos/resellers/photo.jpg",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Response (404 Not Found):** If profile doesn't exist
```json
{
  "detail": "Not found."
}
```

**Response (403 Forbidden):** If user doesn't have RESELLER role
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**Field Descriptions:**
- `id` (read-only): Profile ID
- `user` (read-only): User ID (automatically set to authenticated user)
- `display_name` (required): Public/brand name shown to customers
- `contact_phone` (optional): Contact phone number
- `address` (optional): Business address
- `referral_code` (read-only): Unique referral code (auto-generated)
- `sponsor` (read-only): ID of sponsor (direct upline) reseller profile
- `group_root` (read-only): ID of top-most leader in reseller's tree (auto-calculated)
- `own_commission_rate` (optional): Default commission percentage for own sales (default: 10.00)
- `upline_commission_rate` (optional): Suggested percentage for direct upline commissions (default: 3.00)
- `status` (optional): Status - `PENDING`, `ACTIVE`, or `SUSPENDED`
- `bank_name` (optional): Bank name for commission payouts
- `bank_account_name` (optional): Account holder name
- `bank_account_number` (optional): Bank account number
- `direct_downline_count` (read-only): Count of direct downlines
- `photo` (optional): Profile photo URL (absolute URL if photo is uploaded)
- `created_at` (read-only): Profile creation timestamp
- `updated_at` (read-only): Last update timestamp

**cURL Example:**
```bash
curl -X GET http://localhost:8000/resellers/me/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Python Example:**
```python
import requests

headers = {
    'Authorization': f'Bearer {access_token}'
}

response = requests.get('http://localhost:8000/resellers/me/profile/', headers=headers)
profile = response.json()
print(profile)
```

**JavaScript/Fetch Example:**
```javascript
const response = await fetch('http://localhost:8000/resellers/me/profile/', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});

const profile = await response.json();
console.log(profile);
```

---

## Staff Profile

### Get My Staff Profile

**Endpoint:** `GET /admin/staff/me/profile/`

**Permission:** Authenticated user with `STAFF` role

**Description:** Returns the authenticated staff user's own profile.

**Request:**
```bash
GET /admin/staff/me/profile/
Authorization: Bearer <your_access_token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "user": 789,
  "name": "Jane Smith",
  "job_title": "Operations Manager",
  "department": "Operations",
  "contact_phone": "+1234567890",
  "photo": "http://localhost:8000/media/profile_photos/staff/photo.jpg",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Response (404 Not Found):** If profile doesn't exist
```json
{
  "detail": "Not found."
}
```

**Response (403 Forbidden):** If user doesn't have STAFF role
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**Field Descriptions:**
- `id` (read-only): Profile ID
- `user` (read-only): User ID (automatically set to authenticated user)
- `name` (required): Full name of the staff member
- `job_title` (optional): Job title or position
- `department` (optional): Department or division
- `contact_phone` (optional): Contact phone number
- `photo` (optional): Profile photo URL (absolute URL if photo is uploaded)
- `created_at` (read-only): Profile creation timestamp
- `updated_at` (read-only): Last update timestamp

**cURL Example:**
```bash
curl -X GET http://localhost:8000/admin/staff/me/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Python Example:**
```python
import requests

headers = {
    'Authorization': f'Bearer {access_token}'
}

response = requests.get('http://localhost:8000/admin/staff/me/profile/', headers=headers)
profile = response.json()
print(profile)
```

**JavaScript/Fetch Example:**
```javascript
const response = await fetch('http://localhost:8000/admin/staff/me/profile/', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});

const profile = await response.json();
console.log(profile);
```

---

## List Endpoint Behavior

All "me/profile" endpoints return a single object (not an array) when using the list endpoint. This makes it easier to work with since there's only ever one profile per user.

**Example:**
```bash
GET /suppliers/me/profile/
```

**Response (200 OK) - With Profile:**
```json
{
  "id": 1,
  "user": 123,
  "company_name": "Travel Co",
  "contact_person": "John Doe",
  "contact_phone": "+1234567890",
  "address": "123 Main St, City, Country",
  "tax_id": "TAX123456",
  "status": "ACTIVE",
  "photo": "http://localhost:8000/media/profile_photos/suppliers/photo.jpg",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Response (404 Not Found) - No Profile:**
```json
{
  "detail": "Not found."
}
```

---

## Update Profile

You can update your profile using PUT or PATCH on the detail endpoint with your profile ID. First, get your profile to retrieve the ID, then use it for updates:

### Update Supplier Profile

**Step 1: Get your profile ID**
```bash
GET /suppliers/me/profile/
# Response: {"id": 1, ...}
```

**Step 2: Update using the ID**
```bash
PUT /suppliers/me/profile/1/
Authorization: Bearer <your_access_token>
Content-Type: application/json

{
  "company_name": "Travel Co",
  "contact_person": "John Doe",
  "contact_phone": "+9876543210",
  "address": "456 New Address",
  "tax_id": "TAX123456",
  "status": "ACTIVE"
}
```

**Or use PATCH for partial updates:**
```bash
PATCH /suppliers/me/profile/1/
Authorization: Bearer <your_access_token>
Content-Type: application/json

{
  "contact_phone": "+9876543210",
  "address": "456 New Address"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "user": 123,
  "company_name": "Travel Co",
  "contact_person": "John Doe",
  "contact_phone": "+9876543210",
  "address": "456 New Address",
  "tax_id": "TAX123456",
  "status": "ACTIVE",
  "photo": "http://localhost:8000/media/profile_photos/suppliers/photo.jpg",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-20T11:00:00Z"
}
```

### Update Reseller Profile

**Step 1: Get your profile ID**
```bash
GET /resellers/me/profile/
# Response: {"id": 1, ...}
```

**Step 2: Update using the ID**
```bash
PUT /resellers/me/profile/1/
Authorization: Bearer <your_access_token>
Content-Type: application/json

{
  "display_name": "Updated Agency Name",
  "contact_phone": "+1234567890",
  "address": "456 Business Ave",
  "own_commission_rate": "20.00",
  "upline_commission_rate": "5.00",
  "status": "ACTIVE",
  "bank_name": "Bank Name",
  "bank_account_name": "Account Holder",
  "bank_account_number": "1234567890"
}
```

**Or use PATCH for partial updates:**
```bash
PATCH /resellers/me/profile/1/
Authorization: Bearer <your_access_token>
Content-Type: application/json

{
  "display_name": "Updated Agency Name",
  "own_commission_rate": "20.00"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "user": 456,
  "display_name": "Updated Agency Name",
  "contact_phone": "+1234567890",
  "address": "456 Business Ave",
  "referral_code": "ABC12345",
  "sponsor": 2,
  "group_root": 2,
  "own_commission_rate": "20.00",
  "upline_commission_rate": "5.00",
  "status": "ACTIVE",
  "bank_name": "Bank Name",
  "bank_account_name": "Account Holder",
  "bank_account_number": "1234567890",
  "direct_downline_count": 5,
  "photo": "http://localhost:8000/media/profile_photos/resellers/photo.jpg",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-20T11:00:00Z"
}
```

### Update Staff Profile

**Step 1: Get your profile ID**
```bash
GET /admin/staff/me/profile/
# Response: {"id": 1, ...}
```

**Step 2: Update using the ID**
```bash
PUT /admin/staff/me/profile/1/
Authorization: Bearer <your_access_token>
Content-Type: application/json

{
  "name": "Jane Smith",
  "job_title": "Senior Operations Manager",
  "department": "Senior Operations",
  "contact_phone": "+1234567890"
}
```

**Or use PATCH for partial updates:**
```bash
PATCH /admin/staff/me/profile/1/
Authorization: Bearer <your_access_token>
Content-Type: application/json

{
  "job_title": "Senior Operations Manager",
  "department": "Senior Operations"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "user": 789,
  "name": "Jane Smith",
  "job_title": "Senior Operations Manager",
  "department": "Senior Operations",
  "contact_phone": "+1234567890",
  "photo": "http://localhost:8000/media/profile_photos/staff/photo.jpg",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-20T11:00:00Z"
}
```

**Note:** 
- **PUT** requires all fields (full update)
- **PATCH** allows partial updates (only send fields you want to change)
- Replace `{id}` with your actual profile ID (get it from the GET response)
- The detail endpoint (`/suppliers/me/profile/{id}/`) is the standard DRF way and is required for PUT/PATCH operations

---

## Create Profile

If you don't have a profile yet, you can create one:

### Create Supplier Profile
```bash
POST /suppliers/me/profile/
Authorization: Bearer <your_access_token>
Content-Type: application/json

{
  "company_name": "My Company",
  "contact_person": "John Doe",
  "contact_phone": "+1234567890",
  "address": "123 Main St",
  "tax_id": "TAX123",
  "status": "PENDING"
}
```

### Create Reseller Profile
```bash
POST /resellers/me/profile/
Authorization: Bearer <your_access_token>
Content-Type: application/json

{
  "display_name": "My Travel Agency",
  "contact_phone": "+1234567890",
  "address": "456 Business Ave",
  "own_commission_rate": "15.00",
  "status": "PENDING"
}
```

### Create Staff Profile
```bash
POST /admin/staff/me/profile/
Authorization: Bearer <your_access_token>
Content-Type: application/json

{
  "name": "Jane Smith",
  "job_title": "Operations Manager",
  "department": "Operations",
  "contact_phone": "+1234567890"
}
```

---

## Notes

1. **Authentication Required**: All endpoints require a valid JWT access token in the Authorization header.

2. **Role-Based Access**: You can only access the profile endpoint that matches your user role:
   - Suppliers → `/suppliers/me/profile/`
   - Resellers → `/resellers/me/profile/`
   - Staff → `/admin/staff/me/profile/`

3. **Read-Only Fields**: Some fields are read-only and cannot be updated:
   - `id`, `user`, `created_at`, `updated_at`
   - For resellers: `referral_code`, `group_root`, `direct_downline_count`

4. **Photo Field**: The `photo` field returns an absolute URL if a photo is uploaded, or `null` if no photo exists.

5. **Profile Creation**: If you don't have a profile, you'll get a 404 when trying to retrieve it. Use the POST endpoint to create your profile first.

6. **JWT Token**: Your JWT access token already contains `full_name` and `profile_picture_url` in its payload. You can decode the token to get this information without making an API call. See `AUTHENTICATION.md` for details.

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 400 Bad Request (Validation Error)
```json
{
  "field_name": [
    "Error message describing the validation issue."
  ]
}
```

