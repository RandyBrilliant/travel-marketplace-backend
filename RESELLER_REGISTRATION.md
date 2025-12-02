# Reseller Registration Guide

## Overview
Resellers can register themselves through the public registration endpoint. The system automatically handles referral code generation and sponsor linking.

## Registration Endpoint

**URL:** `POST /users/`

**Authentication:** Not required (public endpoint)

**Content-Type:** `application/json`

---

## Registration Request

### Basic Reseller Registration

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
    "address": "123 Business St, City, Country"
  }
}
```

**Notes:**
- `referral_code` is **automatically generated** if not provided
- `status` defaults to `PENDING` (requires admin approval)
- Commission rates use default values if not specified

### Registration with Sponsor (MLM)

If joining under an existing reseller, provide their referral code:

```json
{
  "email": "newreseller@example.com",
  "phone_number": "+1234567890",
  "password": "SecurePassword123!",
  "password_confirm": "SecurePassword123!",
  "role": "RESELLER",
  "reseller_profile": {
    "display_name": "New Travel Agency",
    "contact_phone": "+1234567890",
    "address": "456 Business Ave, City, Country",
    "sponsor_referral_code": "ABC12345"
  }
}
```

**Notes:**
- `sponsor_referral_code` must belong to an existing active reseller
- The new reseller will automatically join the sponsor's group
- `group_root` is automatically set based on sponsor's hierarchy

### Registration with Custom Referral Code

You can specify your own referral code (must be unique):

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
    "referral_code": "MYCODE123",
    "own_commission_rate": "12.50",
    "bank_name": "Bank Name",
    "bank_account_name": "Account Holder Name",
    "bank_account_number": "123456789"
  }
}
```

---

## Request Fields

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | Valid email address (must be unique) |
| `password` | string | Password (must meet Django validation requirements) |
| `password_confirm` | string | Password confirmation (must match password) |
| `role` | string | Must be `"RESELLER"` |
| `reseller_profile.display_name` | string | Public/brand name shown to customers |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `phone_number` | string | Primary phone number |
| `reseller_profile.contact_phone` | string | Business contact phone |
| `reseller_profile.address` | string | Business address |
| `reseller_profile.referral_code` | string | Custom referral code (8-20 chars, auto-generated if not provided) |
| `reseller_profile.sponsor_referral_code` | string | Referral code of sponsor (if joining under someone) |
| `reseller_profile.own_commission_rate` | decimal | Default: 10.00 |
| `reseller_profile.upline_commission_rate` | decimal | Default: 3.00 |
| `reseller_profile.bank_name` | string | Bank name for payouts |
| `reseller_profile.bank_account_name` | string | Account holder name |
| `reseller_profile.bank_account_number` | string | Bank account number |

---

## Success Response

**Status:** `201 Created`

```json
{
  "message": "User registered successfully.",
  "user": {
    "id": 123,
    "email": "reseller@example.com",
    "phone_number": "+1234567890",
    "role": "RESELLER",
    "email_verified": false,
    "is_active": true,
    "is_staff": false,
    "is_superuser": false,
    "date_joined": "2024-01-15T10:30:00Z"
  }
}
```

**Note:** After registration, resellers can access their profile at:
- `GET /resellers/me/profile/` - View own profile
- `PUT/PATCH /resellers/me/profile/` - Update own profile

---

## Error Responses

### 400 Bad Request - Validation Error

```json
{
  "email": ["This field is required."]
}
```

### 400 Bad Request - Password Mismatch

```json
{
  "password_confirm": ["Password fields didn't match."]
}
```

### 400 Bad Request - Invalid Sponsor Code

```json
{
  "reseller_profile": {
    "sponsor_referral_code": ["Sponsor with referral code 'INVALID' does not exist."]
  }
}
```

### 400 Bad Request - Duplicate Email

```json
{
  "email": ["user with this email address already exists."]
}
```

### 400 Bad Request - Duplicate Referral Code

```json
{
  "reseller_profile": {
    "referral_code": ["reseller profile with this referral code already exists."]
  }
}
```

---

## Registration Flow

1. **Submit Registration**
   - POST to `/users/` with reseller profile data
   - System validates all fields
   - System checks sponsor referral code (if provided)

2. **User Account Creation**
   - User account created with role `RESELLER`
   - Email verification set to `false` (must verify later)

3. **Profile Creation**
   - Reseller profile created
   - Referral code auto-generated if not provided
   - Sponsor linked if `sponsor_referral_code` provided
   - Status set to `PENDING` (requires admin approval)

4. **Post-Registration**
   - Reseller receives confirmation
   - Admin reviews and approves (changes status to `ACTIVE`)
   - Reseller can then login and access the platform

---

## Example cURL Request

```bash
curl -X POST http://localhost:8000/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "reseller@example.com",
    "phone_number": "+1234567890",
    "password": "SecurePassword123!",
    "password_confirm": "SecurePassword123!",
    "role": "RESELLER",
    "reseller_profile": {
      "display_name": "My Travel Agency",
      "contact_phone": "+1234567890",
      "address": "123 Business St"
    }
  }'
```

---

## Example JavaScript/Fetch Request

```javascript
const response = await fetch('http://localhost:8000/users/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'reseller@example.com',
    phone_number: '+1234567890',
    password: 'SecurePassword123!',
    password_confirm: 'SecurePassword123!',
    role: 'RESELLER',
    reseller_profile: {
      display_name: 'My Travel Agency',
      contact_phone: '+1234567890',
      address: '123 Business St, City, Country',
      sponsor_referral_code: 'ABC12345' // Optional: if joining under someone
    }
  })
});

const data = await response.json();
console.log(data);
```

---

## Important Notes

1. **Account Status**: New resellers start with status `PENDING`. Admin must approve before they can fully use the platform.

2. **Referral Code**: 
   - Auto-generated if not provided (8 characters: uppercase letters + numbers)
   - Must be unique if custom code is provided
   - Used to invite other resellers under you

3. **Sponsor/MLM Structure**:
   - Providing `sponsor_referral_code` links you to that reseller's downline
   - You inherit the sponsor's `group_root` for commission calculations
   - Cannot change sponsor after registration

4. **Banking Information**:
   - Can be added during registration or later
   - Required for commission payouts

5. **Email Verification**:
   - Email is not verified automatically
   - Implement email verification endpoint separately

6. **Profile Updates**:
   - After registration, use `/resellers/me/profile/` to update profile
   - Requires authentication (login first)

---

## Next Steps After Registration

1. **Login**: Use the registered email and password to get JWT tokens
   ```
   POST /api/token/
   ```

2. **View Profile**: 
   ```
   GET /resellers/me/profile/
   Authorization: Bearer <your_token>
   ```

3. **Update Profile**: Add banking info, update details
   ```
   PATCH /resellers/me/profile/
   Authorization: Bearer <your_token>
   ```

4. **Wait for Approval**: Admin will review and activate your account

