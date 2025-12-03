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

---

## User Management Endpoints

### Base URL: `/users/`

#### 1. List Users
- **Method:** `GET`
- **Endpoint:** `/users/`
- **Permission:** Admin-only
- **Description:** Returns a paginated list of all users

**Query Parameters:**
- `page` (optional): Page number for pagination
- `page_size` (optional): Number of results per page

**Response (200 OK):**
```json
{
  "count": 100,
  "next": "http://example.com/users/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "email": "user@example.com",
      "phone_number": "+1234567890",
      "role": "SUPPLIER",
      "email_verified": true,
      "email_verified_at": "2024-01-15T10:30:00Z",
      "is_active": true,
      "is_staff": false,
      "is_superuser": false,
      "last_login": "2024-01-20T08:00:00Z",
      "date_joined": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

#### 2. Get User
- **Method:** `GET`
- **Endpoint:** `/users/{id}/`
- **Permission:** Admin-only
- **Description:** Returns specific user details

**Path Parameters:**
- `id` (required): User ID (integer)

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "phone_number": "+1234567890",
  "role": "SUPPLIER",
  "email_verified": true,
  "email_verified_at": "2024-01-15T10:30:00Z",
  "is_active": true,
  "is_staff": false,
  "is_superuser": false,
  "last_login": "2024-01-20T08:00:00Z",
  "date_joined": "2024-01-01T00:00:00Z"
}
```

---

#### 3. Create User (Registration)
- **Method:** `POST`
- **Endpoint:** `/users/`
- **Permission:** Public (no authentication required)
- **Description:** Register a new user account with optional profile creation

**Request Payload:**
```json
{
  "email": "newuser@example.com",
  "phone_number": "+1234567890",
  "password": "SecurePassword123!",
  "password_confirm": "SecurePassword123!",
  "role": "SUPPLIER",
  "supplier_profile": {
    "company_name": "Travel Co",
    "contact_person": "John Doe",
    "contact_phone": "+1234567890",
    "address": "123 Main St, City, Country",
    "tax_id": "TAX123456",
    "status": "PENDING"
  }
}
```

**Field Descriptions:**
- `email` (required, string): Unique email address
- `phone_number` (optional, string): Contact phone number (max 20 chars)
- `password` (required, string): Password (must meet Django's password validation)
- `password_confirm` (required, string): Password confirmation (must match password)
- `role` (required, string): User role - one of: `SUPPLIER`, `RESELLER`, `STAFF`, `CUSTOMER`
- `supplier_profile` (optional, object): Supplier profile data (only if role is SUPPLIER)
- `reseller_profile` (optional, object): Reseller profile data (only if role is RESELLER)
- `staff_profile` (optional, object): Staff profile data (only if role is STAFF)
- `customer_profile` (optional, object): Customer profile data (only if role is CUSTOMER)

**Validation Rules:**
- Password must meet Django's password validation requirements
- `password` and `password_confirm` must match
- Profile data must match the selected role (e.g., cannot provide `supplier_profile` if role is `RESELLER`)
- Email must be unique

**Response (201 Created):**
```json
{
  "message": "User registered successfully.",
  "user": {
    "id": 123,
    "email": "newuser@example.com",
    "phone_number": "+1234567890",
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

**Example with Reseller Profile:**
```json
{
  "email": "reseller@example.com",
  "phone_number": "+1234567890",
  "password": "SecurePassword123!",
  "password_confirm": "SecurePassword123!",
  "role": "RESELLER",
  "reseller_profile": {
    "display_name": "My Travel Agency",
    "contact_phone": "+1234567890",
    "address": "456 Business Ave",
    "sponsor_referral_code": "ABC12345",
    "own_commission_rate": "15.00",
    "upline_commission_rate": "5.00",
    "status": "PENDING",
    "bank_name": "Bank Name",
    "bank_account_name": "Account Holder",
    "bank_account_number": "1234567890"
  }
}
```

**Example with Customer Profile:**
```json
{
  "email": "customer@example.com",
  "phone_number": "+1234567890",
  "password": "SecurePassword123!",
  "password_confirm": "SecurePassword123!",
  "role": "CUSTOMER",
  "customer_profile": {
    "first_name": "Jane",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "address": "789 Street Rd",
    "city": "City",
    "country": "Country",
    "postal_code": "12345",
    "date_of_birth": "1990-01-01",
    "gender": "FEMALE",
    "preferred_language": "en",
    "preferred_currency": "USD",
    "emergency_contact_name": "John Doe",
    "emergency_contact_phone": "+0987654321",
    "travel_interests": ["beach", "adventure", "culture"]
  }
}
```

---

#### 4. Update User
- **Method:** `PUT` or `PATCH`
- **Endpoint:** `/users/{id}/`
- **Permission:** Admin-only
- **Description:** Update user details

**Path Parameters:**
- `id` (required): User ID (integer)

**Request Payload (PUT - Full Update):**
```json
{
  "email": "updated@example.com",
  "phone_number": "+9876543210",
  "role": "RESELLER",
  "is_active": true
}
```

**Request Payload (PATCH - Partial Update):**
```json
{
  "phone_number": "+9876543210"
}
```

**Field Descriptions:**
- `email` (optional, string): Email address (must be unique if changed)
- `phone_number` (optional, string): Contact phone number (max 20 chars)
- `role` (optional, string): User role - one of: `SUPPLIER`, `RESELLER`, `STAFF`, `CUSTOMER`
- `is_active` (optional, boolean): Whether the user account is active

**Read-only Fields (cannot be updated via API):**
- `is_staff`
- `is_superuser`
- `email_verified`
- `email_verified_at`
- `last_login`
- `date_joined`

**Response (200 OK):**
```json
{
  "id": 123,
  "email": "updated@example.com",
  "phone_number": "+9876543210",
  "role": "RESELLER",
  "email_verified": false,
  "email_verified_at": null,
  "is_active": true,
  "is_staff": false,
  "is_superuser": false,
  "last_login": null,
  "date_joined": "2024-01-01T00:00:00Z"
}
```

---

#### 5. Delete User (Disabled)
- **Method:** `DELETE`
- **Endpoint:** `/users/{id}/`
- **Permission:** Admin-only
- **Description:** Delete operation is disabled. Returns 405 Method Not Allowed.

**Response (405 Method Not Allowed):**
```json
{
  "error": "Delete is not allowed. Use the deactivate endpoint instead."
}
```

---

#### 6. Deactivate User
- **Method:** `POST`
- **Endpoint:** `/users/{id}/deactivate/`
- **Permission:** Admin-only
- **Description:** Sets `is_active = False` for the user account

**Path Parameters:**
- `id` (required): User ID (integer)

**Request Payload:** None (empty body)

**Response (200 OK):**
```json
{
  "message": "User user@example.com has been deactivated successfully.",
  "user": {
    "id": 123,
    "email": "user@example.com",
    "phone_number": "+1234567890",
    "role": "SUPPLIER",
    "email_verified": true,
    "email_verified_at": "2024-01-15T10:30:00Z",
    "is_active": false,
    "is_staff": false,
    "is_superuser": false,
    "last_login": "2024-01-20T08:00:00Z",
    "date_joined": "2024-01-01T00:00:00Z"
  }
}
```

---

#### 7. Activate User
- **Method:** `POST`
- **Endpoint:** `/users/{id}/activate/`
- **Permission:** Admin-only
- **Description:** Sets `is_active = True` for the user account

**Path Parameters:**
- `id` (required): User ID (integer)

**Request Payload:** None (empty body)

**Response (200 OK):**
```json
{
  "message": "User user@example.com has been activated successfully.",
  "user": {
    "id": 123,
    "email": "user@example.com",
    "phone_number": "+1234567890",
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
      "updated_at": "2024-01-15T10:30:00Z"
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
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

#### 3. Create Supplier Profile
- **Method:** `POST`
- **Endpoint:** `/admin/suppliers/`
- **Permission:** Admin-only
- **Description:** Create a new supplier profile for an existing user

**Request Payload:**
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
- `user` (required, integer): User ID - must be a user with `SUPPLIER` role
- `company_name` (required, string): Official company/business name (max 255 chars)
- `contact_person` (required, string): Primary contact person name (max 255 chars)
- `contact_phone` (required, string): Primary contact phone number (max 50 chars)
- `address` (optional, string): Business address
- `tax_id` (optional, string): Tax identification number (max 100 chars)
- `status` (optional, string): Status - `PENDING` (default), `ACTIVE`, or `SUSPENDED`

**Validation Rules:**
- User must exist and have `SUPPLIER` role
- User must not already have a supplier profile (OneToOne relationship)
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
  "updated_at": "2024-01-20T10:00:00Z"
}
```

---

#### 4. Update Supplier Profile
- **Method:** `PUT` or `PATCH`
- **Endpoint:** `/admin/suppliers/{id}/`
- **Permission:** Admin-only
- **Description:** Update supplier profile details

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
  "contact_phone": "+9876543210"
}
```

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
  "updated_at": "2024-01-20T11:00:00Z"
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
      "updated_at": "2024-01-15T10:30:00Z"
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
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

#### 3. Create Reseller Profile
- **Method:** `POST`
- **Endpoint:** `/admin/resellers/`
- **Permission:** Admin-only
- **Description:** Create a new reseller profile for an existing user

**Request Payload:**
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
- `user` (required, integer): User ID - must be a user with `RESELLER` role
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

**Read-only Fields (auto-set):**
- `group_root`: Automatically set based on sponsor hierarchy
- `direct_downline_count`: Count of direct downlines

**Validation Rules:**
- User must exist and have `RESELLER` role
- User must not already have a reseller profile (OneToOne relationship)
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
  "updated_at": "2024-01-20T10:00:00Z"
}
```

---

#### 4. Update Reseller Profile
- **Method:** `PUT` or `PATCH`
- **Endpoint:** `/admin/resellers/{id}/`
- **Permission:** Admin-only
- **Description:** Update reseller profile details

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
  "own_commission_rate": "20.00"
}
```

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
  "updated_at": "2024-01-20T11:00:00Z"
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
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
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
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

#### 3. Create Staff Profile
- **Method:** `POST`
- **Endpoint:** `/admin/staff/`
- **Permission:** Admin-only
- **Description:** Create a new staff profile for an existing user

**Request Payload:**
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
- `user` (required, integer): User ID - must be a user with `STAFF` role
- `name` (required, string): Full name of the staff member (max 255 chars)
- `job_title` (optional, string): Job title or position (max 255 chars)
- `department` (optional, string): Department or division (max 255 chars)
- `contact_phone` (optional, string): Contact phone number (max 50 chars)

**Validation Rules:**
- User must exist and have `STAFF` role
- User must not already have a staff profile (OneToOne relationship)

**Response (201 Created):**
```json
{
  "id": 1,
  "user": 789,
  "name": "Jane Smith",
  "job_title": "Operations Manager",
  "department": "Operations",
  "contact_phone": "+1234567890",
  "created_at": "2024-01-20T10:00:00Z",
  "updated_at": "2024-01-20T10:00:00Z"
}
```

---

#### 4. Update Staff Profile
- **Method:** `PUT` or `PATCH`
- **Endpoint:** `/admin/staff/{id}/`
- **Permission:** Admin-only
- **Description:** Update staff profile details

**Path Parameters:**
- `id` (required): Staff profile ID (integer)

**Request Payload (PUT - Full Update):**
```json
{
  "user": 789,
  "name": "Jane Smith Updated",
  "job_title": "Senior Operations Manager",
  "department": "Operations",
  "contact_phone": "+9876543210"
}
```

**Request Payload (PATCH - Partial Update):**
```json
{
  "job_title": "Senior Operations Manager",
  "department": "Senior Operations"
}
```

**Read-only Fields (cannot be updated):**
- `id`
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
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-20T11:00:00Z"
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

### Customer Profiles

#### Base URL: `/admin/customers/`

#### 1. List Customer Profiles
- **Method:** `GET`
- **Endpoint:** `/admin/customers/`
- **Permission:** Admin-only
- **Description:** List all customer profiles with filtering and search

**Query Parameters:**
- `country` (optional): Filter by country name
- `gender` (optional): Filter by gender - `MALE`, `FEMALE`, or `OTHER`
- `user__is_active` (optional): Filter by user active status - `true` or `false`
- `search` (optional): Search across `first_name`, `last_name`, `email`, `phone_number`, `city`, `country`
- `page` (optional): Page number for pagination
- `page_size` (optional): Number of results per page

**Example Request:**
```
GET /admin/customers/?country=USA&gender=FEMALE&user__is_active=true&search=John
```

**Response (200 OK):**
```json
{
  "count": 200,
  "next": "http://example.com/admin/customers/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": 101,
      "first_name": "John",
      "last_name": "Doe",
      "full_name": "John Doe",
      "phone_number": "+1234567890",
      "address": "123 Main St",
      "city": "New York",
      "country": "USA",
      "postal_code": "10001",
      "date_of_birth": "1990-01-01",
      "gender": "MALE",
      "preferred_language": "en",
      "preferred_currency": "USD",
      "emergency_contact_name": "Jane Doe",
      "emergency_contact_phone": "+0987654321",
      "travel_interests": ["beach", "adventure"],
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

#### 2. Get Customer Profile
- **Method:** `GET`
- **Endpoint:** `/admin/customers/{id}/`
- **Permission:** Admin-only
- **Description:** Get specific customer profile details

**Path Parameters:**
- `id` (required): Customer profile ID (integer)

**Response (200 OK):**
```json
{
  "id": 1,
  "user": 101,
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "phone_number": "+1234567890",
  "address": "123 Main St",
  "city": "New York",
  "country": "USA",
  "postal_code": "10001",
  "date_of_birth": "1990-01-01",
  "gender": "MALE",
  "preferred_language": "en",
  "preferred_currency": "USD",
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_phone": "+0987654321",
  "travel_interests": ["beach", "adventure", "culture"],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

#### 3. Create Customer Profile
- **Method:** `POST`
- **Endpoint:** `/admin/customers/`
- **Permission:** Admin-only
- **Description:** Create a new customer profile for an existing user

**Request Payload:**
```json
{
  "user": 101,
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "address": "123 Main St",
  "city": "New York",
  "country": "USA",
  "postal_code": "10001",
  "date_of_birth": "1990-01-01",
  "gender": "MALE",
  "preferred_language": "en",
  "preferred_currency": "USD",
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_phone": "+0987654321",
  "travel_interests": ["beach", "adventure", "culture"]
}
```

**Field Descriptions:**
- `user` (required, integer): User ID - must be a user with `CUSTOMER` role
- `first_name` (required, string): Customer's first name (max 255 chars)
- `last_name` (required, string): Customer's last name (max 255 chars)
- `phone_number` (optional, string): Primary contact phone number (max 50 chars)
- `address` (optional, string): Street address
- `city` (optional, string): City name (max 100 chars)
- `country` (optional, string): Country name (max 100 chars)
- `postal_code` (optional, string): Postal/ZIP code (max 20 chars)
- `date_of_birth` (optional, date): Customer's date of birth (format: YYYY-MM-DD)
- `gender` (optional, string): Gender identity - `MALE`, `FEMALE`, or `OTHER`
- `preferred_language` (optional, string): Preferred language code (default: "en", max 10 chars)
- `preferred_currency` (optional, string): Preferred currency code (default: "IDR", max 10 chars)
- `emergency_contact_name` (optional, string): Name of emergency contact person (max 255 chars)
- `emergency_contact_phone` (optional, string): Phone number of emergency contact (max 50 chars)
- `travel_interests` (optional, array): List of travel interests/preferences (JSON array of strings)

**Read-only Fields:**
- `full_name`: Automatically computed from `first_name` and `last_name`

**Validation Rules:**
- User must exist and have `CUSTOMER` role
- User must not already have a customer profile (OneToOne relationship)
- `date_of_birth` must be a valid date in YYYY-MM-DD format
- `gender` must be one of: `MALE`, `FEMALE`, `OTHER`
- `travel_interests` must be a valid JSON array

**Response (201 Created):**
```json
{
  "id": 1,
  "user": 101,
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "phone_number": "+1234567890",
  "address": "123 Main St",
  "city": "New York",
  "country": "USA",
  "postal_code": "10001",
  "date_of_birth": "1990-01-01",
  "gender": "MALE",
  "preferred_language": "en",
  "preferred_currency": "USD",
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_phone": "+0987654321",
  "travel_interests": ["beach", "adventure", "culture"],
  "created_at": "2024-01-20T10:00:00Z",
  "updated_at": "2024-01-20T10:00:00Z"
}
```

---

#### 4. Update Customer Profile
- **Method:** `PUT` or `PATCH`
- **Endpoint:** `/admin/customers/{id}/`
- **Permission:** Admin-only
- **Description:** Update customer profile details

**Path Parameters:**
- `id` (required): Customer profile ID (integer)

**Request Payload (PUT - Full Update):**
```json
{
  "user": 101,
  "first_name": "John",
  "last_name": "Smith",
  "phone_number": "+9876543210",
  "address": "456 New St",
  "city": "Los Angeles",
  "country": "USA",
  "postal_code": "90001",
  "date_of_birth": "1992-05-15",
  "gender": "MALE",
  "preferred_language": "en",
  "preferred_currency": "USD",
  "emergency_contact_name": "Jane Smith",
  "emergency_contact_phone": "+1111111111",
  "travel_interests": ["mountain", "hiking"]
}
```

**Request Payload (PATCH - Partial Update):**
```json
{
  "city": "Los Angeles",
  "travel_interests": ["mountain", "hiking", "adventure"]
}
```

**Read-only Fields (cannot be updated):**
- `id`
- `full_name` (computed from first_name and last_name)
- `created_at`
- `updated_at`

**Response (200 OK):**
```json
{
  "id": 1,
  "user": 101,
  "first_name": "John",
  "last_name": "Smith",
  "full_name": "John Smith",
  "phone_number": "+9876543210",
  "address": "456 New St",
  "city": "Los Angeles",
  "country": "USA",
  "postal_code": "90001",
  "date_of_birth": "1992-05-15",
  "gender": "MALE",
  "preferred_language": "en",
  "preferred_currency": "USD",
  "emergency_contact_name": "Jane Smith",
  "emergency_contact_phone": "+1111111111",
  "travel_interests": ["mountain", "hiking", "adventure"],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-20T11:00:00Z"
}
```

---

#### 5. Delete Customer Profile (Disabled)
- **Method:** `DELETE`
- **Endpoint:** `/admin/customers/{id}/`
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

1. **Delete is Disabled**: All DELETE operations return 405 Method Not Allowed. Deactivate users instead using `/users/{id}/deactivate/`.

2. **User Field**: In admin serializers, the `user` field is writable and must reference a user with the correct role:
   - Supplier profiles require a user with `SUPPLIER` role
   - Reseller profiles require a user with `RESELLER` role
   - Staff profiles require a user with `STAFF` role
   - Customer profiles require a user with `CUSTOMER` role

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

12. **Travel Interests**: The `travel_interests` field for customers accepts a JSON array of strings. Example: `["beach", "adventure", "culture"]`.
