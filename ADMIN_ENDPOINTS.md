# Admin Endpoints Documentation

## Overview
Admin-only CRUD endpoints for managing all user roles and profiles. Delete operations are disabled - use the deactivate endpoint instead.

## Authentication
All admin endpoints require:
- Admin user authentication (JWT token)
- `is_staff = True` permission

**Authentication Header:**
```
Authorization: Bearer <your_jwt_token>
```

**Note:** The JWT access token payload includes user information (`email`, `role`, `full_name`, `profile_picture_url`). You can decode the token to access this information without making additional API calls. See `AUTHENTICATION.md` for details on decoding JWT tokens.

## User Management

### Get Current User Information

**Endpoint:** `GET /users/me/`

**Permission:** Authenticated user (any role)

**Description:** Get current authenticated user information including role and profile name.

**Response (200 OK):**
```json
{
  "id": 123,
  "email": "supplier@example.com",
  "role": "SUPPLIER",
  "email_verified": true,
  "email_verified_at": "2024-01-15T10:30:00Z",
  "is_active": true,
  "is_staff": false,
  "is_superuser": false,
  "last_login": "2024-01-20T08:00:00Z",
  "date_joined": "2024-01-01T00:00:00Z",
  "name": "ABC Travel Company"
}
```

**Note:** The `name` field is derived from the user's profile:
- Suppliers: `company_name` from SupplierProfile
- Resellers: `display_name` from ResellerProfile  
- Staff: `name` from StaffProfile
- Fallback: `email` if no profile exists

---

## Admin Profile Management Endpoints

### Supplier Profiles

#### Base URL: `/admin/suppliers/`

#### 1. List Supplier Profiles
- **Method:** `GET`
- **Endpoint:** `/admin/suppliers/`
- **Permission:** Admin-only
- **Description:** List all supplier profiles with filtering and search

**Query Parameters:**
- `status` (optional): Filter by status - `PENDING`, `ACTIVE`, or `SUSPENDED`
- `user__is_active` (optional): Filter by user active status - `true` or `false`
- `search` (optional): Search across `company_name`, `contact_person`, `email`, `tax_id`
- `page` (optional): Page number for pagination
- `page_size` (optional): Number of results per page

**Example Request:**
```
GET /admin/suppliers/?status=ACTIVE&user__is_active=true&search=Travel
```

**Response (200 OK):**
```json
{
  "count": 50,
  "next": "http://example.com/admin/suppliers/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": 123,
      "company_name": "Travel Co",
      "contact_person": "John Doe",
      "contact_phone": "+1234567890",
      "address": "123 Main St, City, Country",
      "tax_id": "TAX123456",
      "status": "ACTIVE",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "user_data": {
        "id": 123,
        "email": "supplier@example.com",
        "role": "SUPPLIER",
        "email_verified": true,
        "email_verified_at": "2024-01-15T10:30:00Z",
        "is_active": true,
        "is_staff": false,
        "is_superuser": false,
        "last_login": "2024-01-20T08:00:00Z",
        "date_joined": "2024-01-01T00:00:00Z"
      },
      "photo": "http://localhost:8000/media/profile_photos/suppliers/photo.jpg"
    }
  ]
}
```

---

#### 2. Get Supplier Profile
- **Method:** `GET`
- **Endpoint:** `/admin/suppliers/{id}/`
- **Permission:** Admin-only
- **Description:** Get specific supplier profile details

**Path Parameters:**
- `id` (required): Supplier profile ID (integer)

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
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
      "user_data": {
        "id": 123,
        "email": "supplier@example.com",
        "role": "SUPPLIER",
        "email_verified": true,
        "email_verified_at": "2024-01-15T10:30:00Z",
        "is_active": true,
        "is_staff": false,
        "is_superuser": false,
        "last_login": "2024-01-20T08:00:00Z",
        "date_joined": "2024-01-01T00:00:00Z"
      },
      "photo": "http://localhost:8000/media/profile_photos/suppliers/photo.jpg"
}
```

---

#### 3. Create Supplier Profile
- **Method:** `POST`
- **Endpoint:** `/admin/suppliers/`
- **Permission:** Admin-only
- **Description:** Create a new supplier profile. Can create a new user automatically or use an existing user.

**Request Payload (Option 1 - Auto-create User):**
```json
{
  "company_name": "Travel Co",
  "contact_person": "John Doe",
  "contact_phone": "+1234567890",
  "address": "123 Main St, City, Country",
  "tax_id": "TAX123456",
  "status": "PENDING",
  "email": "supplier@example.com",
  "password": "SecurePassword123!"
}
```

**Request Payload (Option 2 - Use Existing User):**
```json
{
  "user": 123,
  "company_name": "Travel Co",
  "contact_person": "John Doe",
  "contact_phone": "+1234567890",
  "address": "123 Main St, City, Country",
  "tax_id": "TAX123456",
  "status": "PENDING"
}
```

**Field Descriptions:**
- `user` (optional, integer): User ID - must be a user with `SUPPLIER` role (if provided, user must exist)
- `company_name` (required, string): Official company/business name (max 255 chars)
- `contact_person` (required, string): Primary contact person name (max 255 chars)
- `contact_phone` (required, string): Primary contact phone number (max 50 chars)
- `address` (optional, string): Business address
- `tax_id` (optional, string): Tax identification number (max 100 chars)
- `status` (optional, string): Status - `PENDING` (default), `ACTIVE`, or `SUSPENDED`
- `photo` (optional, file): Profile photo (uploaded file, stored in `profile_photos/suppliers/`)

**User Creation Fields (when `user` is not provided):**
- `email` (required if creating user, string): Email address for the new user (must be unique)
- `password` (required if creating user, string): Password for the new user (must meet Django's password validation)

**Validation Rules:**
- If `user` is provided: User must exist and have `SUPPLIER` role, and must not already have a supplier profile
- If `user` is not provided: `email` and `password` are required to create a new user
- Password must meet Django's password validation requirements
- Email must be unique
- Status must be one of: `PENDING`, `ACTIVE`, `SUSPENDED`

**Response (201 Created):**
```json
{
  "id": 1,
  "user": 123,
  "company_name": "Travel Co",
  "contact_person": "John Doe",
  "contact_phone": "+1234567890",
  "address": "123 Main St, City, Country",
  "tax_id": "TAX123456",
  "status": "PENDING",
  "created_at": "2024-01-20T10:00:00Z",
  "updated_at": "2024-01-20T10:00:00Z",
      "user_data": {
        "id": 123,
        "email": "supplier@example.com",
        "role": "SUPPLIER",
        "email_verified": false,
        "email_verified_at": null,
        "is_active": true,
        "is_staff": false,
        "is_superuser": false,
        "last_login": null,
    "date_joined": "2024-01-20T10:00:00Z"
  }
}
```

---

#### 4. Update Supplier Profile
- **Method:** `PUT` or `PATCH`
- **Endpoint:** `/admin/suppliers/{id}/`
- **Permission:** Admin-only
- **Description:** Update supplier profile details. Can also update associated user email.

**Path Parameters:**
- `id` (required): Supplier profile ID (integer)

**Request Payload (PUT - Full Update):**
```json
{
  "user": 123,
  "company_name": "Updated Travel Co",
  "contact_person": "Jane Smith",
  "contact_phone": "+9876543210",
  "address": "456 New St, City, Country",
  "tax_id": "TAX789012",
  "status": "ACTIVE"
}
```

**Request Payload (PATCH - Partial Update):**
```json
{
  "status": "ACTIVE",
  "contact_phone": "+9876543210",
  "email": "newemail@example.com"
}
```

**User Update Fields:**
- `email` (optional, string): Update the associated user's email address (must be unique)

**Note:** Phone numbers are stored in the profile (`contact_phone`), not in the user account.

**Note:** `is_active` and `password` cannot be updated through this endpoint. Use dedicated endpoints for user status and password management.

**Read-only Fields (cannot be updated):**
- `id`
- `created_at`
- `updated_at`

**Response (200 OK):**
```json
{
  "id": 1,
  "user": 123,
  "company_name": "Updated Travel Co",
  "contact_person": "Jane Smith",
  "contact_phone": "+9876543210",
  "address": "456 New St, City, Country",
  "tax_id": "TAX789012",
  "status": "ACTIVE",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-20T11:00:00Z",
  "user_data": {
    "id": 123,
    "email": "newemail@example.com",
,
    "role": "SUPPLIER",
    "email_verified": true,
    "email_verified_at": "2024-01-15T10:30:00Z",
    "is_active": true,
    "is_staff": false,
    "is_superuser": false,
    "last_login": "2024-01-20T08:00:00Z",
    "date_joined": "2024-01-01T00:00:00Z"
  }
}
```

---

#### 5. Delete Supplier Profile (Disabled)
- **Method:** `DELETE`
- **Endpoint:** `/admin/suppliers/{id}/`
- **Permission:** Admin-only
- **Description:** Delete operation is disabled. Returns 405 Method Not Allowed.

**Response (405 Method Not Allowed):**
```json
{
  "error": "Delete is not allowed. Deactivate the associated user account instead."
}
```

---

### Reseller Profiles

#### Base URL: `/admin/resellers/`

#### 1. List Reseller Profiles
- **Method:** `GET`
- **Endpoint:** `/admin/resellers/`
- **Permission:** Admin-only
- **Description:** List all reseller profiles with filtering and search

**Query Parameters:**
- `status` (optional): Filter by status - `PENDING`, `ACTIVE`, or `SUSPENDED`
- `user__is_active` (optional): Filter by user active status - `true` or `false`
- `search` (optional): Search across `display_name`, `email`, `referral_code`, `bank_account_name`, `bank_account_number`
- `page` (optional): Page number for pagination
- `page_size` (optional): Number of results per page

**Example Request:**
```
GET /admin/resellers/?status=ACTIVE&user__is_active=true&search=Travel
```

**Response (200 OK):**
```json
{
  "count": 75,
  "next": "http://example.com/admin/resellers/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": 456,
      "display_name": "My Travel Agency",
      "contact_phone": "+1234567890",
      "address": "456 Business Ave",
      "referral_code": "ABC12345",
      "sponsor": null,
      "group_root": 1,
      "own_commission_rate": "15.00",
      "upline_commission_rate": "5.00",
      "status": "ACTIVE",
      "bank_name": "Bank Name",
      "bank_account_name": "Account Holder",
      "bank_account_number": "1234567890",
      "direct_downline_count": 5,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "user_data": {
        "id": 456,
        "email": "reseller@example.com",
        "role": "RESELLER",
        "email_verified": true,
        "email_verified_at": "2024-01-15T10:30:00Z",
        "is_active": true,
        "is_staff": false,
        "is_superuser": false,
        "last_login": "2024-01-20T08:00:00Z",
        "date_joined": "2024-01-01T00:00:00Z"
      }
    }
  ]
}
```

---

#### 2. Get Reseller Profile
- **Method:** `GET`
- **Endpoint:** `/admin/resellers/{id}/`
- **Permission:** Admin-only
- **Description:** Get specific reseller profile details

**Path Parameters:**
- `id` (required): Reseller profile ID (integer)

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
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "user_data": {
    "id": 456,
    "email": "reseller@example.com",
    "role": "RESELLER",
    "email_verified": true,
    "email_verified_at": "2024-01-15T10:30:00Z",
    "is_active": true,
    "is_staff": false,
    "is_superuser": false,
    "last_login": "2024-01-20T08:00:00Z",
    "date_joined": "2024-01-01T00:00:00Z"
  }
}
```

---

#### 3. Create Reseller Profile
- **Method:** `POST`
- **Endpoint:** `/admin/resellers/`
- **Permission:** Admin-only
- **Description:** Create a new reseller profile. Can create a new user automatically or use an existing user.

**Request Payload (Option 1 - Auto-create User):**
```json
{
  "display_name": "My Travel Agency",
  "contact_phone": "+1234567890",
  "address": "456 Business Ave",
  "referral_code": "ABC12345",
  "sponsor": 2,
  "own_commission_rate": "15.00",
  "upline_commission_rate": "5.00",
  "status": "PENDING",
  "bank_name": "Bank Name",
  "bank_account_name": "Account Holder",
  "bank_account_number": "1234567890",
  "email": "reseller@example.com",
  "password": "SecurePassword123!",
}
```

**Request Payload (Option 2 - Use Existing User):**
```json
{
  "user": 456,
  "display_name": "My Travel Agency",
  "contact_phone": "+1234567890",
  "address": "456 Business Ave",
  "referral_code": "ABC12345",
  "sponsor": 2,
  "own_commission_rate": "15.00",
  "upline_commission_rate": "5.00",
  "status": "PENDING",
  "bank_name": "Bank Name",
  "bank_account_name": "Account Holder",
  "bank_account_number": "1234567890"
}
```

**Field Descriptions:**
- `user` (optional, integer): User ID - must be a user with `RESELLER` role (if provided, user must exist)
- `display_name` (required, string): Public/brand name shown to customers (max 255 chars)
- `contact_phone` (optional, string): Contact phone number (max 50 chars)
- `address` (optional, string): Business address
- `referral_code` (optional, string): Unique referral code (max 20 chars, auto-generated if not provided)
- `sponsor` (optional, integer): ID of sponsor (direct upline) reseller profile
- `own_commission_rate` (optional, decimal): Default commission percentage for own sales (default: 10.00, max 5 digits, 2 decimal places)
- `upline_commission_rate` (optional, decimal): Suggested percentage for direct upline commissions (default: 3.00, max 5 digits, 2 decimal places)
- `status` (optional, string): Status - `PENDING` (default), `ACTIVE`, or `SUSPENDED`
- `bank_name` (optional, string): Bank name for commission payouts (max 255 chars)
- `bank_account_name` (optional, string): Account holder name (max 255 chars)
- `bank_account_number` (optional, string): Bank account number (max 100 chars)

**User Creation Fields (when `user` is not provided):**
- `email` (required if creating user, string): Email address for the new user (must be unique)
- `password` (required if creating user, string): Password for the new user (must meet Django's password validation)

**Read-only Fields (auto-set):**
- `group_root`: Automatically set based on sponsor hierarchy
- `direct_downline_count`: Count of direct downlines

**Validation Rules:**
- If `user` is provided: User must exist and have `RESELLER` role, and must not already have a reseller profile
- If `user` is not provided: `email` and `password` are required to create a new user
- Password must meet Django's password validation requirements
- Email must be unique
- `referral_code` must be unique (auto-generated if not provided)
- `sponsor` must be a valid reseller profile ID if provided
- Status must be one of: `PENDING`, `ACTIVE`, `SUSPENDED`
- Commission rates must be valid decimal numbers

**Response (201 Created):**
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
  "status": "PENDING",
  "bank_name": "Bank Name",
  "bank_account_name": "Account Holder",
  "bank_account_number": "1234567890",
  "direct_downline_count": 0,
  "created_at": "2024-01-20T10:00:00Z",
  "updated_at": "2024-01-20T10:00:00Z",
  "user_data": {
    "id": 456,
    "email": "reseller@example.com",
    "role": "RESELLER",
    "email_verified": false,
    "email_verified_at": null,
    "is_active": true,
    "is_staff": false,
    "is_superuser": false,
    "last_login": null,
    "date_joined": "2024-01-20T10:00:00Z"
  }
}
```

---

#### 4. Update Reseller Profile
- **Method:** `PUT` or `PATCH`
- **Endpoint:** `/admin/resellers/{id}/`
- **Permission:** Admin-only
- **Description:** Update reseller profile details. Can also update associated user email.

**Path Parameters:**
- `id` (required): Reseller profile ID (integer)

**Request Payload (PUT - Full Update):**
```json
{
  "user": 456,
  "display_name": "Updated Travel Agency",
  "contact_phone": "+9876543210",
  "address": "789 New Ave",
  "referral_code": "XYZ67890",
  "sponsor": 3,
  "own_commission_rate": "20.00",
  "upline_commission_rate": "7.00",
  "status": "ACTIVE",
  "bank_name": "New Bank",
  "bank_account_name": "New Holder",
  "bank_account_number": "9876543210"
}
```

**Request Payload (PATCH - Partial Update):**
```json
{
  "status": "ACTIVE",
  "own_commission_rate": "20.00",
  "email": "newemail@example.com",
}
```

**User Update Fields:**
- `email` (optional, string): Update the associated user's email address (must be unique)
**Note:** Phone numbers are stored in the profile (`contact_phone`), not in the user account.

**Note:** `is_active` and `password` cannot be updated through this endpoint. Use dedicated endpoints for user status and password management.

**Read-only Fields (cannot be updated):**
- `id`
- `group_root` (auto-calculated based on sponsor)
- `direct_downline_count` (auto-calculated)
- `created_at`
- `updated_at`

**Response (200 OK):**
```json
{
  "id": 1,
  "user": 456,
  "display_name": "Updated Travel Agency",
  "contact_phone": "+9876543210",
  "address": "789 New Ave",
  "referral_code": "XYZ67890",
  "sponsor": 3,
  "group_root": 3,
  "own_commission_rate": "20.00",
  "upline_commission_rate": "7.00",
  "status": "ACTIVE",
  "bank_name": "New Bank",
  "bank_account_name": "New Holder",
  "bank_account_number": "9876543210",
  "direct_downline_count": 5,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-20T11:00:00Z",
  "user_data": {
    "id": 456,
    "email": "newemail@example.com",
,
    "role": "RESELLER",
    "email_verified": true,
    "email_verified_at": "2024-01-15T10:30:00Z",
    "is_active": true,
    "is_staff": false,
    "is_superuser": false,
    "last_login": "2024-01-20T08:00:00Z",
    "date_joined": "2024-01-01T00:00:00Z"
  }
}
```

---

#### 5. Delete Reseller Profile (Disabled)
- **Method:** `DELETE`
- **Endpoint:** `/admin/resellers/{id}/`
- **Permission:** Admin-only
- **Description:** Delete operation is disabled. Returns 405 Method Not Allowed.

**Response (405 Method Not Allowed):**
```json
{
  "error": "Delete is not allowed. Deactivate the associated user account instead."
}
```

---

### Staff Profiles

#### Base URL: `/admin/staff/`

#### 1. List Staff Profiles
- **Method:** `GET`
- **Endpoint:** `/admin/staff/`
- **Permission:** Admin-only
- **Description:** List all staff profiles with filtering and search

**Query Parameters:**
- `department` (optional): Filter by department name
- `user__is_active` (optional): Filter by user active status - `true` or `false`
- `search` (optional): Search across `name`, `job_title`, `department`, `email`
- `page` (optional): Page number for pagination
- `page_size` (optional): Number of results per page

**Example Request:**
```
GET /admin/staff/?department=Operations&user__is_active=true&search=Manager
```

**Response (200 OK):**
```json
{
  "count": 25,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": 789,
      "name": "Jane Smith",
      "job_title": "Operations Manager",
      "department": "Operations",
      "contact_phone": "+1234567890",
      "photo": "http://localhost:8000/media/profile_photos/staff/photo.jpg",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "user_data": {
        "id": 789,
        "email": "jane.smith@example.com",
        "role": "STAFF",
        "email_verified": true,
        "email_verified_at": "2024-01-15T10:30:00Z",
        "is_active": true,
        "is_staff": true,
        "is_superuser": false,
        "last_login": "2024-01-20T08:00:00Z",
        "date_joined": "2024-01-01T00:00:00Z"
      }
    }
  ]
}
```

---

#### 2. Get Staff Profile
- **Method:** `GET`
- **Endpoint:** `/admin/staff/{id}/`
- **Permission:** Admin-only
- **Description:** Get specific staff profile details

**Path Parameters:**
- `id` (required): Staff profile ID (integer)

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
  "updated_at": "2024-01-15T10:30:00Z",
  "user_data": {
    "id": 789,
    "email": "jane.smith@example.com",
    "role": "STAFF",
    "email_verified": true,
    "email_verified_at": "2024-01-15T10:30:00Z",
    "is_active": true,
    "is_staff": true,
    "is_superuser": false,
    "last_login": "2024-01-20T08:00:00Z",
    "date_joined": "2024-01-01T00:00:00Z"
  }
}
```

---

#### 3. Create Staff Profile
- **Method:** `POST`
- **Endpoint:** `/admin/staff/`
- **Permission:** Admin-only
- **Description:** Create a new staff profile. Can create a new user automatically or use an existing user.

**Request Payload (Option 1 - Auto-create User):**
```json
{
  "name": "Jane Smith",
  "job_title": "Operations Manager",
  "department": "Operations",
  "contact_phone": "+1234567890",
  "email": "jane.smith@example.com",
  "password": "SecurePassword123!",
}
```

**Request Payload (Option 2 - Use Existing User):**
```json
{
  "user": 789,
  "name": "Jane Smith",
  "job_title": "Operations Manager",
  "department": "Operations",
  "contact_phone": "+1234567890"
}
```

**Field Descriptions:**
- `user` (optional, integer): User ID - must be a user with `STAFF` role (if provided, user must exist)
- `name` (required, string): Full name of the staff member (max 255 chars)
- `job_title` (optional, string): Job title or position (max 255 chars)
- `department` (optional, string): Department or division (max 255 chars)
- `contact_phone` (optional, string): Contact phone number (max 50 chars)
- `photo` (optional, file): Profile photo (uploaded file, stored in `profile_photos/staff/`)
- `photo` (optional, file): Profile photo (uploaded file)

**User Creation Fields (when `user` is not provided):**
- `email` (required if creating user, string): Email address for the new user (must be unique)
- `password` (required if creating user, string): Password for the new user (must meet Django's password validation)

**Validation Rules:**
- If `user` is provided: User must exist and have `STAFF` role, and must not already have a staff profile
- If `user` is not provided: `email` and `password` are required to create a new user
- Password must meet Django's password validation requirements
- Email must be unique

**Response (201 Created):**
```json
{
  "id": 1,
  "user": 789,
  "name": "Jane Smith",
  "job_title": "Operations Manager",
  "department": "Operations",
  "contact_phone": "+1234567890",
  "photo": null,
  "created_at": "2024-01-20T10:00:00Z",
  "updated_at": "2024-01-20T10:00:00Z",
  "user_data": {
    "id": 789,
    "email": "jane.smith@example.com",
    "role": "STAFF",
    "email_verified": false,
    "email_verified_at": null,
    "is_active": true,
    "is_staff": true,
    "is_superuser": false,
    "last_login": null,
    "date_joined": "2024-01-20T10:00:00Z"
  }
}
```

---

#### 4. Update Staff Profile
- **Method:** `PUT` or `PATCH`
- **Endpoint:** `/admin/staff/{id}/`
- **Permission:** Admin-only
- **Description:** Update staff profile details. Can also update associated user email.

**Path Parameters:**
- `id` (required): Staff profile ID (integer)

**Request Payload (PUT - Full Update):**
```json
{
  "user": 789,
  "name": "Jane Smith Updated",
  "job_title": "Senior Operations Manager",
  "department": "Senior Operations",
  "contact_phone": "+9876543210",
  "email": "newemail@example.com"
}
```

**Request Payload (PATCH - Partial Update):**
```json
{
  "name": "Jane Smith Updated",
  "email": "newemail@example.com"
}
```

**User Update Fields:**
- `email` (optional, string): Update the associated user's email address (must be unique)
**Note:** Phone numbers are stored in the profile (`contact_phone`), not in the user account.

**Note:** `is_active` and `password` cannot be updated through this endpoint. Use dedicated endpoints for user status and password management.

**Field Descriptions:**
- Profile fields: `name`, `job_title`, `department`, `contact_phone`, `photo`

**Read-only Fields (cannot be updated):**
- `id`
- `user` (user ID cannot be changed, but user data can be updated)
- `user_data` (read-only, shows current user data)
- `created_at`
- `updated_at`

**Response (200 OK):**
```json
{
  "id": 1,
  "user": 789,
  "name": "Jane Smith Updated",
  "job_title": "Senior Operations Manager",
  "department": "Senior Operations",
  "contact_phone": "+9876543210",
  "photo": "http://localhost:8000/media/profile_photos/staff/photo.jpg",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-20T11:00:00Z",
      "user_data": {
        "id": 789,
        "email": "newemail@example.com",
,
        "role": "STAFF",
        "email_verified": true,
        "email_verified_at": "2024-01-15T10:30:00Z",
        "is_active": true,
        "is_staff": true,
        "is_superuser": false,
        "last_login": "2024-01-20T08:00:00Z",
        "date_joined": "2024-01-01T00:00:00Z"
      }
}
```

---

#### 5. Delete Staff Profile (Disabled)
- **Method:** `DELETE`
- **Endpoint:** `/admin/staff/{id}/`
- **Permission:** Admin-only
- **Description:** Delete operation is disabled. Returns 405 Method Not Allowed.

**Response (405 Method Not Allowed):**
```json
{
  "error": "Delete is not allowed. Deactivate the associated user account instead."
}
```

---

## Error Responses

### 400 Bad Request (Validation Error)
```json
{
  "field_name": [
    "Error message describing the validation issue."
  ],
  "non_field_errors": [
    "General validation error message."
  ]
}
```

**Example:**
```json
{
  "email": [
    "This field is required."
  ],
  "password": [
    "This password is too short. It must contain at least 8 characters."
  ],
  "password_confirm": [
    "Password fields didn't match."
  ]
}
```

### 401 Unauthorized (Missing/Invalid Token)
```json
{
  "detail": "Authentication credentials were not provided."
}
```

or

```json
{
  "detail": "Given token not valid for any token type"
}
```

### 403 Forbidden (Non-Admin)
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

### 405 Method Not Allowed (Delete Attempt)
```json
{
  "error": "Delete is not allowed. Deactivate the associated user account instead."
}
```

### 409 Conflict (Duplicate Profile)
```json
{
  "user": [
    "User with this user already has a profile."
  ]
}
```

---

## Notes

1. **Delete is Disabled**: All DELETE operations return 405 Method Not Allowed. User management is handled through the role-specific profile endpoints (e.g., `/admin/suppliers/`, `/admin/resellers/`, `/admin/staff/`).

2. **User Field**: In admin serializers, the `user` field is writable and must reference a user with the correct role:
   - Supplier profiles require a user with `SUPPLIER` role
   - Reseller profiles require a user with `RESELLER` role
   - Staff profiles require a user with `STAFF` role

3. **Permissions**: All admin endpoints require `is_staff = True` on the authenticated user.

4. **Filtering**: Use query parameters for filtering (e.g., `?status=ACTIVE`, `?user__is_active=true`).

5. **Search**: Use `?search=term` for text search across multiple fields. The search is case-insensitive and searches across all configured search fields.

6. **Profile Creation**: When creating profiles via admin endpoints:
   - The user must already exist
   - The user must have the correct role
   - The profile must not already exist (OneToOne relationship)

7. **Pagination**: All list endpoints support pagination. Use `page` and `page_size` query parameters.

8. **Date Formats**: All dates should be in ISO 8601 format (YYYY-MM-DD for dates, YYYY-MM-DDTHH:MM:SSZ for datetimes).

9. **Commission Rates**: Commission rates are stored as decimal numbers with 2 decimal places. Maximum value is 999.99.

10. **Referral Codes**: For resellers, if `referral_code` is not provided during creation, a unique 8-character code will be auto-generated.

11. **Group Root**: For resellers, `group_root` is automatically calculated based on the sponsor hierarchy. If no sponsor exists, the reseller becomes their own group root.

12. **JWT Token Payload**: The access token includes user information (`email`, `role`, `full_name`, `profile_picture_url`) in its payload. Decode the token to access this information without making additional API calls. See `AUTHENTICATION.md` for details on decoding JWT tokens.
