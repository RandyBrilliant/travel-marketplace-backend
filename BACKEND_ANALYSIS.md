# Backend Structure Analysis

## 📋 Overview

This is a **Django REST Framework** backend for a travel marketplace platform with a multi-role user system (Suppliers, Resellers, Staff). The backend follows a well-structured approach with separate apps for account management and travel product management.

---

## 🏗️ Architecture

### **Technology Stack**
- **Framework**: Django 5.2.8
- **API Framework**: Django REST Framework 3.16.1
- **Authentication**: JWT via `djangorestframework-simplejwt` 5.5.1
- **Database**: SQLite (development) / PostgreSQL (production-ready via `dj-database-url`)
- **File Storage**: Local filesystem with `Pillow` for image handling
- **CORS**: `django-cors-headers` for cross-origin requests
- **Filtering**: `django-filter` for advanced query filtering

### **Project Structure**
```
travel-marketplace-backend/
├── backend/              # Main project settings
│   ├── settings.py       # Configuration
│   ├── urls.py          # URL routing
│   └── wsgi.py          # WSGI config
├── account/             # User & profile management app
│   ├── models.py        # CustomUser, SupplierProfile, ResellerProfile, StaffProfile
│   ├── views.py         # Profile ViewSets
│   ├── serializers.py   # Profile serializers
│   ├── token_views.py   # JWT authentication views
│   └── managers.py      # Custom user manager
└── travel/              # Tour package management app
    ├── models.py        # TourPackage, TourDate, Booking, Payment, etc.
    ├── views.py         # Tour management ViewSets
    └── serializers.py   # Tour serializers
```

---

## 👥 User Management System

### **User Roles**
Three distinct user roles with role-based access control:

1. **SUPPLIER**: Creates and manages tour packages
   - Has `SupplierProfile` with company details
   - Can manage their own tours, dates, images, itinerary items

2. **RESELLER**: Sells tours to customers
   - Has `ResellerProfile` with MLM (Multi-Level Marketing) structure
   - Supports sponsor/upline/downline relationships
   - Commission tracking per booking
   - Banking info for payouts

3. **STAFF**: Internal admin/operations staff
   - Has `StaffProfile` with job title/department
   - Can manage all profiles (admin endpoints)

### **User Model (`CustomUser`)**
- **Unique Identifier**: Email (not username)
- **Removed Fields**: `username`, `first_name`, `last_name`
- **Role-Based**: `role` field (SUPPLIER, RESELLER, STAFF)
- **Email Verification**: `email_verified`, `email_verified_at`
- **Audit Trail**: `created_by`, `updated_by` (self-referential)

### **Profile Pattern**
Each user role has a **one-to-one** profile model:
- `SupplierProfile` ← `CustomUser`
- `ResellerProfile` ← `CustomUser`
- `StaffProfile` ← `CustomUser`

**Design Decision**: Separates authentication concerns (`CustomUser`) from business data (profiles)

---

## 🎯 Core Models & Relationships

### **Account App Models**

#### `CustomUser`
- Base authentication model
- Email-based authentication
- Role-based permissions

#### `SupplierProfile`
- Company information (name, tax_id, contact details)
- Status: PENDING → ACTIVE → SUSPENDED
- Profile photo support

#### `ResellerProfile`
- **MLM Structure**:
  - `sponsor`: Direct upline who invited this reseller
  - `group_root`: Top-most leader in the tree
  - `referral_code`: Unique code for inviting new members
- **Commission Settings**:
  - `own_commission_rate`: Default 10%
  - `upline_commission_rate`: Default 3%
- **Banking Info**: For commission payouts
- **Auto-maintains** `group_root` based on sponsor hierarchy

#### `StaffProfile`
- Internal staff information
- Job title, department, contact info

### **Travel App Models**

#### `TourPackage`
- Main tour product model
- **Key Fields**:
  - Location: `city`, `country`
  - Duration: `days`, `nights`
  - Pricing: `base_price`, `currency`
  - Tour type: `CONVENTIONAL` or `MUSLIM` (for Indonesian market)
  - Categories: `ADVENTURE`, `CULTURAL`, `BEACH`, etc.
  - Badges: `BEST_SELLER`, `POPULAR`, `TOP_RATED`, `NEW`
- **JSON Fields**: `tags`, `highlights`, `inclusions`, `exclusions`
- **Commission Settings**: Admin-only editable
- **Related**: `supplier` (ForeignKey), `dates`, `images`, `itinerary_items`

#### `TourDate`
- Specific departure dates for a package
- Price can vary per date
- Seat inventory management (`total_seats`, `remaining_seats`)
- Auto-generates `SeatSlot` objects on creation

#### `SeatSlot`
- Individual seat management per tour date
- Stores passenger information (passport, visa, personal details)
- Status: `AVAILABLE`, `RESERVED`, `BOOKED`, `CANCELLED`
- Linked to `Booking` when booked

#### `Booking`
- Reseller booking for a tour date
- Customer information
- Linked to multiple `SeatSlot` objects
- Status: `PENDING`, `CONFIRMED`, `CANCELLED`

#### `Payment`
- Manual payment tracking with upload proof
- Transfer details (sender account, bank, proof image)
- Status: `PENDING`, `APPROVED`, `REJECTED`
- Reviewed by staff

#### `ResellerCommission`
- Commission tracking per booking
- Supports multi-level commissions (level 0 = booking owner, level 1+ = uplines)
- Amount calculated based on tour package commission settings

---

## 🔐 Authentication & Authorization

### **JWT Authentication**
- **Access Token**: 5 minutes (default, configurable)
- **Refresh Token**: 7 days (default, configurable)
- **Token Rotation**: Enabled (old refresh tokens blacklisted)
- **Token Payload Includes**:
  - `email`, `role`
  - `full_name` (from profile)
  - `profile_picture_url` (absolute URL)

### **Permission Classes**
1. **`IsAuthenticated`**: Standard authenticated users
2. **`IsAdminUser`**: Staff with `is_staff=True` for admin endpoints
3. **`IsSupplier`**: Custom permission for supplier-only endpoints

### **API Endpoints**

#### **Public Endpoints**
- `POST /api/token/` - Obtain JWT tokens
- `POST /api/token/refresh/` - Refresh access token

#### **Profile Endpoints** (Self-Management)
- `GET/PUT/PATCH /suppliers/me/profile/` - Supplier's own profile
- `GET/PUT/PATCH /resellers/me/profile/` - Reseller's own profile
- `GET/PUT/PATCH /admin/staff/me/profile/` - Staff's own profile

#### **Tour Management** (Supplier-Only)
- `GET/POST /suppliers/me/tours/` - List/create tours
- `GET/PUT/PATCH/DELETE /suppliers/me/tours/{id}/` - Tour CRUD
- `GET/POST /suppliers/me/tour-dates/` - Manage tour dates
- `GET/POST /suppliers/me/tour-images/` - Manage tour images
- `GET/POST /suppliers/me/itinerary-items/` - Manage itinerary

#### **Admin Endpoints** (Staff-Only)
- `GET/POST/PUT/PATCH /admin/suppliers/` - Manage all suppliers
- `GET/POST/PUT/PATCH /admin/resellers/` - Manage all resellers
- `GET/POST/PUT/PATCH /admin/staff/` - Manage all staff

**Note**: Delete operations are disabled - deactivate users instead.

---

## 🎨 Design Patterns & Best Practices

### ✅ **Strengths**

1. **Separation of Concerns**
   - Auth logic (`CustomUser`) separated from business data (profiles)
   - Two apps: `account` (users) and `travel` (products)

2. **Role-Based Access Control**
   - Clear role system with permission classes
   - ViewSets automatically filter by user role

3. **Custom User Manager**
   - Email-based authentication
   - Proper user/superuser creation methods

4. **Audit Trail**
   - `created_by`, `updated_by` on CustomUser
   - Timestamps (`created_at`, `updated_at`) on all models

5. **Database Indexing**
   - Strategic indexes on frequently queried fields
   - Composite indexes for common query patterns

6. **MLM Structure**
   - Well-designed reseller hierarchy
   - Automatic `group_root` maintenance
   - Referral code system

7. **Flexible Data Storage**
   - JSON fields for flexible data (tags, highlights, etc.)
   - Image uploads with organized media structure

8. **Documentation**
   - Comprehensive markdown docs for endpoints
   - Clear API structure

### ⚠️ **Potential Issues & Improvements**

1. **Missing Features** (Not implemented yet)
   - No public-facing tour browsing endpoints (only supplier management)
   - No booking creation endpoints for resellers
   - No payment upload endpoints for resellers
   - No commission calculation automation
   - No email verification system implementation

2. **Security Considerations**
   - Email verification exists in model but no implementation
   - No rate limiting visible
   - Consider adding request throttling

3. **Data Consistency**
   - `TourDate.remaining_seats` should be calculated from `SeatSlot.status` rather than stored
   - `Booking.seats_booked` redundancy with `seat_slots.count()`

4. **Performance**
   - Missing `select_related`/`prefetch_related` in some querysets
   - No pagination configured in settings (may need custom pagination)

5. **Error Handling**
   - Could benefit from custom exception handlers
   - Some validation logic could be more centralized

6. **Testing**
   - `tests.py` files exist but appear empty
   - No test coverage visible

7. **Configuration**
   - Secret key generation on-the-fly if not set (good for dev, risky for prod)
   - Missing `.env` file example for all required variables

8. **Database**
   - Using SQLite in development (fine)
   - PostgreSQL support via `dj-database-url` (production-ready)

---

## 📦 Dependencies

### **Core**
- `Django==5.2.8`
- `djangorestframework==3.16.1`
- `djangorestframework-simplejwt==5.5.1`

### **Utilities**
- `django-cors-headers==4.9.0` - CORS handling
- `django-filter==25.2` - Advanced filtering
- `dj-database-url==3.0.1` - Database URL parsing
- `Pillow==12.0.0` - Image processing
- `psycopg2-binary==2.9.11` - PostgreSQL adapter

### **Production**
- `gunicorn==23.0.0` - WSGI server

---

## 🔧 Configuration

### **Environment Variables** (from `settings.py`)
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode (boolean)
- `ALLOWED_HOSTS` - Comma-separated host list
- `CSRF_TRUSTED_ORIGINS` - Comma-separated origins
- `DATABASE_URL` - PostgreSQL connection string
- `CORS_ALLOWED_ORIGINS` - Comma-separated CORS origins
- `ACCESS_TOKEN_LIFETIME_MINUTES` - JWT access token lifetime (default: 5)
- `REFRESH_TOKEN_LIFETIME_DAYS` - JWT refresh token lifetime (default: 7)

### **REST Framework Settings**
- **Authentication**: JWT + Session
- **Permissions**: `IsAuthenticatedOrReadOnly` (default)
- **Filtering**: DjangoFilterBackend

### **JWT Settings**
- Access token: 5 minutes
- Refresh token: 7 days
- Token rotation: Enabled
- Blacklist after rotation: Enabled

---

## 🚀 Deployment

### **Docker Support**
- `Dockerfile` present
- `docker-compose.yml` for development
- `entrypoint.sh` for container initialization

### **Production Considerations**
- Gunicorn configured
- Static files collection supported
- Media files handling configured
- Database URL parsing for PostgreSQL

---

## 📊 Model Relationships Summary

```
CustomUser (1) ──── (1) SupplierProfile
                    (1) ResellerProfile
                    (1) StaffProfile

SupplierProfile (1) ──── (*) TourPackage
                              │
                              ├─── (*) TourDate ──── (*) SeatSlot ──── (1) Booking
                              ├─── (*) TourImage
                              └─── (*) ItineraryItem

ResellerProfile (1) ──── (*) Booking ──── (1) Payment
                              │
                              └─── (*) ResellerCommission

ResellerProfile (self-referential)
    ├─── sponsor (FK to ResellerProfile)
    └─── group_root (FK to ResellerProfile)
```

---

## 🎯 Recommendations

### **High Priority**
1. **Implement Public Tour Endpoints**
   - Browse/search tours for resellers
   - Tour detail view with dates/pricing
   - Filtering by category, location, dates

2. **Implement Booking Flow**
   - Reseller booking creation
   - Seat selection logic
   - Booking confirmation workflow

3. **Payment System**
   - Reseller payment upload endpoint
   - Admin payment review/approval workflow

4. **Email Verification**
   - Implement email sending (use Django email backend)
   - Verification link/OTP system

### **Medium Priority**
1. **Add Tests**
   - Unit tests for models
   - API endpoint tests
   - Permission tests

2. **Performance Optimization**
   - Add pagination configuration
   - Optimize querysets with `select_related`/`prefetch_related`
   - Add database query optimization

3. **Error Handling**
   - Custom exception handlers
   - Standardized error responses

4. **Security Enhancements**
   - Rate limiting
   - Input validation hardening
   - CSRF protection review

### **Low Priority**
1. **Documentation**
   - API schema generation (OpenAPI/Swagger)
   - More inline code comments

2. **Monitoring & Logging**
   - Structured logging
   - Performance monitoring
   - Error tracking

---

## 📝 Summary

This is a **well-structured Django REST Framework backend** with:
- ✅ Clean separation of concerns
- ✅ Role-based access control
- ✅ Comprehensive user/profile system
- ✅ Flexible tour package management
- ✅ MLM support for resellers
- ✅ Commission tracking foundation
- ✅ JWT authentication with custom payload

**Next Steps**: Focus on implementing the missing public-facing endpoints and booking/payment workflows to complete the marketplace functionality.

