# Admin Endpoints Documentation

## Overview
Admin-only CRUD endpoints for managing all user roles and profiles. Delete operations are disabled - use the deactivate endpoint instead.

## Authentication
All admin endpoints require:
- Admin user authentication (JWT token)
- `is_staff = True` permission

---

## User Management Endpoints

### Base URL: `/users/`

#### List Users
- **GET** `/users/`
- Returns all users
- Admin-only

#### Get User
- **GET** `/users/{id}/`
- Returns specific user details
- Admin-only

#### Create User
- **POST** `/users/`
- Public endpoint (for registration)
- Uses `UserRegistrationSerializer`

#### Update User
- **PUT/PATCH** `/users/{id}/`
- Update user details
- Admin-only

#### Delete User (Disabled)
- **DELETE** `/users/{id}/`
- Returns 405 Method Not Allowed
- Use deactivate endpoint instead

#### Deactivate User
- **POST** `/users/{id}/deactivate/`
- Sets `is_active = False`
- Admin-only

#### Activate User
- **POST** `/users/{id}/activate/`
- Sets `is_active = True`
- Admin-only

---

## Admin Profile Management Endpoints

### Supplier Profiles

#### Base URL: `/admin/suppliers/`

- **GET** `/admin/suppliers/` - List all supplier profiles
- **GET** `/admin/suppliers/{id}/` - Get specific supplier profile
- **POST** `/admin/suppliers/` - Create new supplier profile
- **PUT/PATCH** `/admin/suppliers/{id}/` - Update supplier profile
- **DELETE** `/admin/suppliers/{id}/` - Disabled (405 error)

**Filters:**
- `?status=PENDING|ACTIVE|SUSPENDED`
- `?user__is_active=true|false`

**Search:**
- `?search=company_name|contact_person|email|tax_id`

**Fields:**
- `user` (writable) - Must be a user with SUPPLIER role
- `company_name`, `contact_person`, `contact_phone`
- `address`, `tax_id`, `status`

---

### Reseller Profiles

#### Base URL: `/admin/resellers/`

- **GET** `/admin/resellers/` - List all reseller profiles
- **GET** `/admin/resellers/{id}/` - Get specific reseller profile
- **POST** `/admin/resellers/` - Create new reseller profile
- **PUT/PATCH** `/admin/resellers/{id}/` - Update reseller profile
- **DELETE** `/admin/resellers/{id}/` - Disabled (405 error)

**Filters:**
- `?status=PENDING|ACTIVE|SUSPENDED`
- `?user__is_active=true|false`

**Search:**
- `?search=display_name|email|referral_code|bank_account_name|bank_account_number`

**Fields:**
- `user` (writable) - Must be a user with RESELLER role
- `display_name`, `contact_phone`, `address`
- `referral_code`, `sponsor`, `group_root` (auto-set)
- `own_commission_rate`, `upline_commission_rate`
- `status`, `bank_name`, `bank_account_name`, `bank_account_number`

---

### Staff Profiles

#### Base URL: `/admin/staff/`

- **GET** `/admin/staff/` - List all staff profiles
- **GET** `/admin/staff/{id}/` - Get specific staff profile
- **POST** `/admin/staff/` - Create new staff profile
- **PUT/PATCH** `/admin/staff/{id}/` - Update staff profile
- **DELETE** `/admin/staff/{id}/` - Disabled (405 error)

**Filters:**
- `?department=department_name`
- `?user__is_active=true|false`

**Search:**
- `?search=name|job_title|department|email`

**Fields:**
- `user` (writable) - Must be a user with STAFF role
- `name`, `job_title`, `department`, `contact_phone`

---

### Customer Profiles

#### Base URL: `/admin/customers/`

- **GET** `/admin/customers/` - List all customer profiles
- **GET** `/admin/customers/{id}/` - Get specific customer profile
- **POST** `/admin/customers/` - Create new customer profile
- **PUT/PATCH** `/admin/customers/{id}/` - Update customer profile
- **DELETE** `/admin/customers/{id}/` - Disabled (405 error)

**Filters:**
- `?country=country_name`
- `?gender=MALE|FEMALE|OTHER`
- `?user__is_active=true|false`

**Search:**
- `?search=first_name|last_name|email|phone_number|city|country`

**Fields:**
- `user` (writable) - Must be a user with CUSTOMER role
- `first_name`, `last_name`, `full_name` (read-only)
- `phone_number`, `address`, `city`, `country`, `postal_code`
- `date_of_birth`, `gender`
- `preferred_language`, `preferred_currency`
- `emergency_contact_name`, `emergency_contact_phone`
- `travel_interests` (JSON array)

---

## Example API Calls

### Deactivate a User
```bash
POST /users/123/deactivate/
Authorization: Bearer <admin_jwt_token>
```

Response:
```json
{
  "message": "User user@example.com has been deactivated successfully.",
  "user": {
    "id": 123,
    "email": "user@example.com",
    "is_active": false,
    ...
  }
}
```

### Create Supplier Profile (Admin)
```bash
POST /admin/suppliers/
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json

{
  "user": 456,
  "company_name": "Travel Co",
  "contact_person": "John Doe",
  "contact_phone": "+1234567890",
  "status": "ACTIVE"
}
```

### List Resellers with Filters
```bash
GET /admin/resellers/?status=ACTIVE&user__is_active=true
Authorization: Bearer <admin_jwt_token>
```

---

## Notes

1. **Delete is Disabled**: All DELETE operations return 405 Method Not Allowed. Deactivate users instead.

2. **User Field**: In admin serializers, the `user` field is writable and must reference a user with the correct role.

3. **Permissions**: All admin endpoints require `is_staff = True` on the authenticated user.

4. **Filtering**: Use query parameters for filtering (e.g., `?status=ACTIVE`)

5. **Search**: Use `?search=term` for text search across multiple fields.

6. **Profile Creation**: When creating profiles via admin endpoints, ensure:
   - The user already exists
   - The user has the correct role
   - The profile doesn't already exist (OneToOne relationship)

---

## Error Responses

### 405 Method Not Allowed (Delete Attempt)
```json
{
  "error": "Delete is not allowed. Deactivate the associated user account instead."
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

