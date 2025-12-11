# Supplier Tour Management Endpoints

## Overview

Endpoints for suppliers to create and manage their tour packages, tour dates, images, and itinerary items. All endpoints require supplier authentication and suppliers can only manage their own resources.

---

## Authentication

All supplier tour endpoints require:
- Supplier user authentication (JWT token)
- `SUPPLIER` role

**Authentication Header:**
```
Authorization: Bearer <your_jwt_token>
```

**Note:** The JWT access token payload includes user information (`email`, `role`, `full_name`, `profile_picture_url`). You can decode the token to access this information without making additional API calls. See `AUTHENTICATION.md` for details on decoding JWT tokens.

---

## Tour Packages

### Base URL: `/api/suppliers/me/tours/`

### 1. List Tour Packages

**Method:** `GET`  
**Endpoint:** `/api/suppliers/me/tours/`  
**Permission:** Authenticated supplier  
**Description:** List all tour packages belonging to the authenticated supplier

**Request:**
```bash
GET /api/suppliers/me/tours/
Authorization: Bearer <your_access_token>
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "name": "5D4N Tokyo Adventure",
    "slug": "5d4n-tokyo-adventure",
    "summary": "Explore the vibrant city of Tokyo with our comprehensive tour package",
    "city": "Tokyo",
    "country": "Japan",
    "days": 5,
    "nights": 4,
    "duration_display": "5 Days / 4 Nights",
    "tour_type": "CONVENTIONAL",
    "category": "CULTURAL",
    "base_price": "1500.00",
    "currency": "USD",
    "badge": "BEST_SELLER",
    "main_image_url": "http://localhost:8000/media/tours/main/tokyo-main.jpg",
    "is_active": true,
    "is_featured": true,
    "supplier_name": "Travel Co",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

**Field Descriptions:**
- `id` (read-only): Tour package ID
- `name`: Tour package name
- `slug` (read-only): URL-friendly identifier (auto-generated from name)
- `summary`: Short description of the tour
- `city`: City where the tour takes place
- `country`: Country where the tour takes place
- `days`: Number of days
- `nights`: Number of nights
- `duration_display` (read-only): Formatted duration string
- `tour_type`: `CONVENTIONAL` or `MUSLIM` (for Indonesian citizens)
- `category`: `ADVENTURE`, `CULTURAL`, `BEACH`, `CITY_BREAK`, `NATURE`, or `FAMILY`
- `base_price`: Reference price (actual price may vary per date)
- `currency`: Currency code (e.g., `USD`, `IDR`)
- `badge` (optional): `BEST_SELLER`, `POPULAR`, `TOP_RATED`, or `NEW`
- `main_image_url` (read-only): Absolute URL of main image
- `is_active`: Whether the tour is active
- `is_featured`: Whether to feature on homepage
- `supplier_name` (read-only): Supplier company name
- `created_at` (read-only): Creation timestamp

---

### 2. Create Tour Package

**Method:** `POST`  
**Endpoint:** `/api/suppliers/me/tours/`  
**Permission:** Authenticated supplier  
**Description:** Create a new tour package

**Request Body:**
```json
{
  "name": "5D4N Tokyo Adventure",
  "summary": "Explore the vibrant city of Tokyo with our comprehensive tour package",
  "description": "Detailed description of the tour including all activities, accommodations, and highlights.",
  "city": "Tokyo",
  "country": "Japan",
  "days": 5,
  "nights": 4,
  "max_group_size": 12,
  "group_type": "Small Group",
  "tour_type": "CONVENTIONAL",
  "category": "CULTURAL",
  "tags": ["sightseeing", "culture", "food"],
  "highlights": ["Tokyo Tower", "Shibuya Crossing", "Tsukiji Fish Market"],
  "inclusions": ["Hotel accommodation", "Breakfast", "Transportation", "English-speaking guide"],
  "exclusions": ["International flights", "Travel insurance", "Personal expenses"],
  "meeting_point": "Hotel lobby at 8:00 AM",
  "cancellation_policy": "Full refund if cancelled 30 days before departure",
  "important_notes": "Please bring comfortable walking shoes and valid passport",
  "base_price": "1500.00",
  "currency": "USD",
  "badge": "BEST_SELLER",
  "is_active": true,
  "is_featured": false
}
```

**Required Fields:**
- `name`
- `summary`
- `city`
- `country`
- `days`
- `nights`
- `category`
- `base_price`
- `currency`

**Optional Fields:**
- `description`
- `max_group_size` (default: 12)
- `group_type` (default: "Small Group")
- `tour_type` (default: "CONVENTIONAL")
- `tags` (array of strings)
- `highlights` (array of strings)
- `inclusions` (array of strings)
- `exclusions` (array of strings)
- `meeting_point`
- `cancellation_policy`
- `important_notes`
- `badge`
- `is_active` (default: true)
- `is_featured` (default: false)
- `main_image` (file upload)
- `itinerary_pdf` (file upload)

**Note:** The `slug` field is auto-generated from the `name` field if not provided. If a slug with the same name already exists, a number suffix will be added (e.g., `tokyo-adventure-1`).

**Response (201 Created):**
```json
{
  "id": 1,
  "supplier": 1,
  "name": "5D4N Tokyo Adventure",
  "slug": "5d4n-tokyo-adventure",
  "summary": "Explore the vibrant city of Tokyo with our comprehensive tour package",
  "description": "Detailed description...",
  "city": "Tokyo",
  "country": "Japan",
  "days": 5,
  "nights": 4,
  "max_group_size": 12,
  "group_type": "Small Group",
  "tour_type": "CONVENTIONAL",
  "category": "CULTURAL",
  "tags": ["sightseeing", "culture", "food"],
  "highlights": ["Tokyo Tower", "Shibuya Crossing", "Tsukiji Fish Market"],
  "inclusions": ["Hotel accommodation", "Breakfast", "Transportation", "English-speaking guide"],
  "exclusions": ["International flights", "Travel insurance", "Personal expenses"],
  "meeting_point": "Hotel lobby at 8:00 AM",
  "cancellation_policy": "Full refund if cancelled 30 days before departure",
  "important_notes": "Please bring comfortable walking shoes and valid passport",
  "base_price": "1500.00",
  "currency": "USD",
  "badge": "BEST_SELLER",
  "main_image": null,
  "itinerary_pdf": null,
  "is_active": true,
  "is_featured": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Response (400 Bad Request):** Validation errors
```json
{
  "name": ["This field is required."],
  "category": ["Invalid choice."]
}
```

**Response (403 Forbidden):** Not a supplier
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/suppliers/me/tours/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "5D4N Tokyo Adventure",
    "summary": "Explore Tokyo",
    "city": "Tokyo",
    "country": "Japan",
    "days": 5,
    "nights": 4,
    "category": "CULTURAL",
    "base_price": "1500.00",
    "currency": "USD"
  }'
```

**Python Example:**
```python
import requests

url = "http://localhost:8000/api/suppliers/me/tours/"
headers = {
    "Authorization": "Bearer YOUR_ACCESS_TOKEN",
    "Content-Type": "application/json"
}
data = {
    "name": "5D4N Tokyo Adventure",
    "summary": "Explore the vibrant city of Tokyo",
    "city": "Tokyo",
    "country": "Japan",
    "days": 5,
    "nights": 4,
    "category": "CULTURAL",
    "base_price": "1500.00",
    "currency": "USD",
    "tour_type": "CONVENTIONAL",
    "highlights": ["Tokyo Tower", "Shibuya Crossing"],
    "inclusions": ["Hotel accommodation", "Breakfast"]
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

---

### 3. Get Tour Package Details

**Method:** `GET`  
**Endpoint:** `/api/suppliers/me/tours/{id}/`  
**Permission:** Authenticated supplier (own tours only)  
**Description:** Get detailed information about a specific tour package, including nested relations (dates, images, itinerary items)

**Request:**
```bash
GET /api/suppliers/me/tours/1/
Authorization: Bearer <your_access_token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "supplier": 1,
  "supplier_name": "Travel Co",
  "name": "5D4N Tokyo Adventure",
  "slug": "5d4n-tokyo-adventure",
  "summary": "Explore the vibrant city of Tokyo",
  "description": "Detailed description...",
  "city": "Tokyo",
  "country": "Japan",
  "days": 5,
  "nights": 4,
  "duration_display": "5 Days / 4 Nights",
  "max_group_size": 12,
  "group_type": "Small Group",
  "group_size_display": "Small Group (Max 12)",
  "tour_type": "CONVENTIONAL",
  "category": "CULTURAL",
  "tags": ["sightseeing", "culture"],
  "highlights": ["Tokyo Tower", "Shibuya Crossing"],
  "inclusions": ["Hotel accommodation", "Breakfast"],
  "exclusions": ["International flights"],
  "meeting_point": "Hotel lobby at 8:00 AM",
  "cancellation_policy": "Full refund if cancelled 30 days before",
  "important_notes": "Bring comfortable shoes",
  "base_price": "1500.00",
  "currency": "USD",
  "badge": "BEST_SELLER",
  "main_image": "http://localhost:8000/media/tours/main/tokyo-main.jpg",
  "itinerary_pdf": "http://localhost:8000/media/tours/itineraries/tokyo-itinerary.pdf",
  "is_active": true,
  "is_featured": true,
  "itinerary_items": [
    {
      "id": 1,
      "day_number": 1,
      "title": "Arrival in Tokyo",
      "description": "Arrive at Narita Airport, transfer to hotel, welcome dinner"
    },
    {
      "id": 2,
      "day_number": 2,
      "title": "Tokyo City Tour",
      "description": "Visit Tokyo Tower, Shibuya Crossing, and Harajuku"
    }
  ],
  "images": [
    {
      "id": 1,
      "image": "http://localhost:8000/media/tours/gallery/tokyo-1.jpg",
      "caption": "Tokyo Tower",
      "order": 1,
      "is_primary": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "dates": [
    {
      "id": 1,
      "departure_date": "2024-03-01",
      "price": "1500.00",
      "total_seats": 20,
      "remaining_seats": 15,
      "is_high_season": false,
      "available_seats_count": 15,
      "booked_seats_count": 5
    }
  ],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "commission_rate": "10.00",
  "commission_type": "PERCENTAGE",
  "fixed_commission_amount": null,
  "commission_notes": "Standard commission rate"
}
```

**Response (404 Not Found):** Tour not found or doesn't belong to supplier
```json
{
  "detail": "Not found."
}
```

---

### 4. Update Tour Package

**Method:** `PUT` or `PATCH`  
**Endpoint:** `/api/suppliers/me/tours/{id}/`  
**Permission:** Authenticated supplier (own tours only)  
**Description:** Update a tour package. Use `PUT` for full update or `PATCH` for partial update.

**Request Body (PATCH example):**
```json
{
  "is_active": false,
  "is_featured": true,
  "badge": "POPULAR"
}
```

**Response (200 OK):** Returns updated tour package (same format as GET response)

**Response (400 Bad Request):** Validation errors
```json
{
  "base_price": ["Ensure this value is greater than or equal to 0."]
}
```

**Response (404 Not Found):** Tour not found or doesn't belong to supplier

**Note:** Commission fields (`commission_rate`, `commission_type`, `fixed_commission_amount`, `commission_notes`) are read-only for suppliers and can only be modified by admin users.

---

### 5. Delete Tour Package

**Method:** `DELETE`  
**Endpoint:** `/api/suppliers/me/tours/{id}/`  
**Permission:** Authenticated supplier (own tours only)  
**Description:** Delete a tour package. This will also delete all associated tour dates, images, and itinerary items.

**Request:**
```bash
DELETE /api/suppliers/me/tours/1/
Authorization: Bearer <your_access_token>
```

**Response (204 No Content):** Tour package deleted successfully

**Response (404 Not Found):** Tour not found or doesn't belong to supplier

---

## Tour Dates

### Base URL: `/api/suppliers/me/tour-dates/`

### 1. List Tour Dates

**Method:** `GET`  
**Endpoint:** `/api/suppliers/me/tour-dates/`  
**Permission:** Authenticated supplier  
**Description:** List all tour dates for packages belonging to the authenticated supplier

**Request:**
```bash
GET /api/suppliers/me/tour-dates/
Authorization: Bearer <your_access_token>
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "departure_date": "2024-03-01",
    "price": "1500.00",
    "total_seats": 20,
    "remaining_seats": 15,
    "is_high_season": false,
    "available_seats_count": 15,
    "booked_seats_count": 5
  },
  {
    "id": 2,
    "departure_date": "2024-03-15",
    "price": "1800.00",
    "total_seats": 20,
    "remaining_seats": 20,
    "is_high_season": true,
    "available_seats_count": 20,
    "booked_seats_count": 0
  }
]
```

**Field Descriptions:**
- `id` (read-only): Tour date ID
- `departure_date`: Date of departure (YYYY-MM-DD format)
- `price`: Price for this specific date
- `total_seats`: Total number of seats available
- `remaining_seats` (read-only): Number of seats still available (auto-calculated)
- `is_high_season`: Whether this date is considered high season
- `available_seats_count` (read-only): Count of available seat slots
- `booked_seats_count` (read-only): Count of booked seat slots

---

### 2. Create Tour Date

**Method:** `POST`  
**Endpoint:** `/api/suppliers/me/tour-dates/`  
**Permission:** Authenticated supplier  
**Description:** Create a new tour date for one of your tour packages

**Request Body:**
```json
{
  "package": 1,
  "departure_date": "2024-03-01",
  "price": "1500.00",
  "total_seats": 20,
  "is_high_season": false
}
```

**Required Fields:**
- `package`: Tour package ID (must belong to the supplier)
- `departure_date`: Date in YYYY-MM-DD format
- `price`: Price for this date
- `total_seats`: Number of seats available

**Optional Fields:**
- `is_high_season` (default: false)

**Response (201 Created):**
```json
{
  "id": 1,
  "departure_date": "2024-03-01",
  "price": "1500.00",
  "total_seats": 20,
  "remaining_seats": 20,
  "is_high_season": false,
  "available_seats_count": 20,
  "booked_seats_count": 0
}
```

**Response (400 Bad Request):** Validation errors
```json
{
  "package": ["Tour package not found or you don't have permission to access it."],
  "departure_date": ["A tour date with this departure date already exists for this package."]
}
```

**Note:** When a tour date is created, seat slots are automatically generated based on `total_seats`. The `remaining_seats` field is automatically calculated.

---

### 3. Get Tour Date Details

**Method:** `GET`  
**Endpoint:** `/api/suppliers/me/tour-dates/{id}/`  
**Permission:** Authenticated supplier (own tour dates only)

**Response (200 OK):** Same format as list response, single object

---

### 4. Update Tour Date

**Method:** `PUT` or `PATCH`  
**Endpoint:** `/api/suppliers/me/tour-dates/{id}/`  
**Permission:** Authenticated supplier (own tour dates only)

**Request Body (PATCH example):**
```json
{
  "price": "1600.00",
  "is_high_season": true
}
```

**Response (200 OK):** Returns updated tour date

**Note:** You cannot change `total_seats` after creation. To modify seats, you may need to delete and recreate the tour date, or manage seat slots directly through the booking system.

---

### 5. Delete Tour Date

**Method:** `DELETE`  
**Endpoint:** `/api/suppliers/me/tour-dates/{id}/`  
**Permission:** Authenticated supplier (own tour dates only)

**Response (204 No Content):** Tour date deleted successfully

**Warning:** Deleting a tour date will also delete all associated seat slots and may affect existing bookings.

---

## Tour Images

### Base URL: `/api/suppliers/me/tour-images/`

### 1. List Tour Images

**Method:** `GET`  
**Endpoint:** `/api/suppliers/me/tour-images/`  
**Permission:** Authenticated supplier  
**Description:** List all tour images for packages belonging to the authenticated supplier

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "image": "http://localhost:8000/media/tours/gallery/tokyo-1.jpg",
    "caption": "Tokyo Tower at sunset",
    "order": 1,
    "is_primary": true,
    "created_at": "2024-01-01T00:00:00Z"
  },
  {
    "id": 2,
    "image": "http://localhost:8000/media/tours/gallery/tokyo-2.jpg",
    "caption": "Shibuya Crossing",
    "order": 2,
    "is_primary": false,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

**Field Descriptions:**
- `id` (read-only): Image ID
- `image`: Image file URL (absolute URL)
- `caption` (optional): Caption/description for the image
- `order`: Display order (lower numbers appear first)
- `is_primary`: Whether this is a primary image (shown first)
- `created_at` (read-only): Upload timestamp

---

### 2. Create Tour Image

**Method:** `POST`  
**Endpoint:** `/api/suppliers/me/tour-images/`  
**Permission:** Authenticated supplier  
**Description:** Upload a new image for one of your tour packages

**Request (multipart/form-data):**
```bash
POST /api/suppliers/me/tour-images/
Content-Type: multipart/form-data

package: 1
image: <file>
caption: Tokyo Tower at sunset
order: 1
is_primary: true
```

**Required Fields:**
- `package`: Tour package ID (must belong to the supplier)
- `image`: Image file (JPEG, PNG, etc.)

**Optional Fields:**
- `caption`: Image caption
- `order` (default: 0): Display order
- `is_primary` (default: false): Whether this is a primary image

**Response (201 Created):**
```json
{
  "id": 1,
  "image": "http://localhost:8000/media/tours/gallery/tokyo-1.jpg",
  "caption": "Tokyo Tower at sunset",
  "order": 1,
  "is_primary": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/suppliers/me/tour-images/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "package=1" \
  -F "image=@/path/to/image.jpg" \
  -F "caption=Tokyo Tower at sunset" \
  -F "order=1" \
  -F "is_primary=true"
```

**Python Example:**
```python
import requests

url = "http://localhost:8000/api/suppliers/me/tour-images/"
headers = {
    "Authorization": "Bearer YOUR_ACCESS_TOKEN"
}
files = {
    "image": ("tokyo-1.jpg", open("/path/to/image.jpg", "rb"), "image/jpeg")
}
data = {
    "package": 1,
    "caption": "Tokyo Tower at sunset",
    "order": 1,
    "is_primary": True
}

response = requests.post(url, files=files, data=data, headers=headers)
print(response.json())
```

---

### 3. Get Tour Image Details

**Method:** `GET`  
**Endpoint:** `/api/suppliers/me/tour-images/{id}/`  
**Permission:** Authenticated supplier (own images only)

**Response (200 OK):** Same format as list response, single object

---

### 4. Update Tour Image

**Method:** `PUT` or `PATCH`  
**Endpoint:** `/api/suppliers/me/tour-images/{id}/`  
**Permission:** Authenticated supplier (own images only)

**Request Body (PATCH example):**
```json
{
  "caption": "Updated caption",
  "order": 2,
  "is_primary": false
}
```

**Response (200 OK):** Returns updated image

**Note:** To replace the image file, you can upload a new file using `PUT` with `multipart/form-data`.

---

### 5. Delete Tour Image

**Method:** `DELETE`  
**Endpoint:** `/api/suppliers/me/tour-images/{id}/`  
**Permission:** Authenticated supplier (own images only)

**Response (204 No Content):** Image deleted successfully

---

## Itinerary Items

### Base URL: `/api/suppliers/me/itinerary-items/`

### 1. List Itinerary Items

**Method:** `GET`  
**Endpoint:** `/api/suppliers/me/itinerary-items/`  
**Permission:** Authenticated supplier  
**Description:** List all itinerary items for packages belonging to the authenticated supplier

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "day_number": 1,
    "title": "Arrival in Tokyo",
    "description": "Arrive at Narita Airport, transfer to hotel, welcome dinner at local restaurant"
  },
  {
    "id": 2,
    "day_number": 2,
    "title": "Tokyo City Tour",
    "description": "Visit Tokyo Tower, Shibuya Crossing, and Harajuku district"
  },
  {
    "id": 3,
    "day_number": 3,
    "title": "Day Trip to Mount Fuji",
    "description": "Full day excursion to Mount Fuji with lunch included"
  }
]
```

**Field Descriptions:**
- `id` (read-only): Itinerary item ID
- `day_number`: Day number (1, 2, 3, etc.)
- `title`: Title/heading for the day
- `description` (optional): Detailed description of activities for the day

---

### 2. Create Itinerary Item

**Method:** `POST`  
**Endpoint:** `/api/suppliers/me/itinerary-items/`  
**Permission:** Authenticated supplier  
**Description:** Create a new itinerary item (day) for one of your tour packages

**Request Body:**
```json
{
  "package": 1,
  "day_number": 1,
  "title": "Arrival in Tokyo",
  "description": "Arrive at Narita Airport, transfer to hotel, welcome dinner at local restaurant"
}
```

**Required Fields:**
- `package`: Tour package ID (must belong to the supplier)
- `day_number`: Day number (must be unique per package)
- `title`: Title for the day

**Optional Fields:**
- `description`: Detailed description

**Response (201 Created):**
```json
{
  "id": 1,
  "day_number": 1,
  "title": "Arrival in Tokyo",
  "description": "Arrive at Narita Airport, transfer to hotel, welcome dinner at local restaurant"
}
```

**Response (400 Bad Request):** Validation errors
```json
{
  "package": ["Tour package not found or you don't have permission to access it."],
  "day_number": ["An itinerary item with this day number already exists for this package."]
}
```

---

### 3. Get Itinerary Item Details

**Method:** `GET`  
**Endpoint:** `/api/suppliers/me/itinerary-items/{id}/`  
**Permission:** Authenticated supplier (own items only)

**Response (200 OK):** Same format as list response, single object

---

### 4. Update Itinerary Item

**Method:** `PUT` or `PATCH`  
**Endpoint:** `/api/suppliers/me/itinerary-items/{id}/`  
**Permission:** Authenticated supplier (own items only)

**Request Body (PATCH example):**
```json
{
  "title": "Updated Day 1 Title",
  "description": "Updated description with more details"
}
```

**Response (200 OK):** Returns updated itinerary item

---

### 5. Delete Itinerary Item

**Method:** `DELETE`  
**Endpoint:** `/api/suppliers/me/itinerary-items/{id}/`  
**Permission:** Authenticated supplier (own items only)

**Response (204 No Content):** Itinerary item deleted successfully

---

## Nested Actions (Alternative Methods)

Instead of using separate endpoints, you can also manage dates, images, and itinerary items through nested actions on the tour package endpoint.

### Manage Tour Dates

**Method:** `GET` or `POST`  
**Endpoint:** `/api/suppliers/me/tours/{id}/dates/`  
**Permission:** Authenticated supplier (own tours only)

**GET Request:** List all dates for a specific tour package
```bash
GET /api/suppliers/me/tours/1/dates/
Authorization: Bearer <your_access_token>
```

**POST Request:** Create a new date for a specific tour package
```bash
POST /api/suppliers/me/tours/1/dates/
Authorization: Bearer <your_access_token>
Content-Type: application/json

{
  "departure_date": "2024-03-01",
  "price": "1500.00",
  "total_seats": 20,
  "is_high_season": false
}
```

**Response:** Same format as the tour dates endpoints

---

### Manage Tour Images

**Method:** `GET` or `POST`  
**Endpoint:** `/api/suppliers/me/tours/{id}/images/`  
**Permission:** Authenticated supplier (own tours only)

**GET Request:** List all images for a specific tour package
```bash
GET /api/suppliers/me/tours/1/images/
Authorization: Bearer <your_access_token>
```

**POST Request:** Upload a new image for a specific tour package
```bash
POST /api/suppliers/me/tours/1/images/
Authorization: Bearer <your_access_token>
Content-Type: multipart/form-data

image: <file>
caption: Tokyo Tower
order: 1
is_primary: true
```

**Response:** Same format as the tour images endpoints

---

### Manage Itinerary Items

**Method:** `GET` or `POST`  
**Endpoint:** `/api/suppliers/me/tours/{id}/itinerary/`  
**Permission:** Authenticated supplier (own tours only)

**GET Request:** List all itinerary items for a specific tour package
```bash
GET /api/suppliers/me/tours/1/itinerary/
Authorization: Bearer <your_access_token>
```

**POST Request:** Create a new itinerary item for a specific tour package
```bash
POST /api/suppliers/me/tours/1/itinerary/
Authorization: Bearer <your_access_token>
Content-Type: application/json

{
  "day_number": 1,
  "title": "Arrival in Tokyo",
  "description": "Arrive at Narita Airport, transfer to hotel"
}
```

**Response:** Same format as the itinerary items endpoints

**Note:** When using nested actions, you don't need to specify the `package` field in the request body as it's automatically set to the tour package ID from the URL.

---

## Common Error Responses

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

### 400 Bad Request (Validation Errors)
```json
{
  "field_name": ["Error message 1", "Error message 2"],
  "another_field": ["Error message"]
}
```

---

## Notes

1. **Slug Auto-Generation:** The `slug` field is automatically generated from the tour package `name` if not provided. If a slug with the same name already exists, a number suffix will be added automatically.

2. **Commission Fields:** Commission-related fields (`commission_rate`, `commission_type`, `fixed_commission_amount`, `commission_notes`) are read-only for suppliers and can only be modified by admin users.

3. **Seat Slot Generation:** When a tour date is created, seat slots are automatically generated based on the `total_seats` value. The `remaining_seats` field is automatically calculated and updated.

4. **File Uploads:** When uploading images or PDF files, use `multipart/form-data` content type. The maximum file size is determined by your Django settings.

5. **Ownership:** Suppliers can only access and modify their own tour packages and related resources. Attempting to access another supplier's resources will result in a 404 Not Found error.

6. **Supplier Profile Required:** Before creating tour packages, ensure you have completed your supplier profile setup. If your supplier profile doesn't exist, you'll receive an error when trying to create tours.

---

## Tour Type Options

- `CONVENTIONAL`: Conventional Tour (default)
- `MUSLIM`: Muslim Tour (for Indonesian citizens)

## Category Options

- `ADVENTURE`: Adventure tours
- `CULTURAL`: Cultural tours
- `BEACH`: Beach tours
- `CITY_BREAK`: City break tours
- `NATURE`: Nature tours
- `FAMILY`: Family-friendly tours

## Badge Options

- `BEST_SELLER`: Best Seller badge
- `POPULAR`: Popular badge
- `TOP_RATED`: Top Rated badge
- `NEW`: New badge

---

## Example Workflow

1. **Create a Tour Package:**
   ```bash
   POST /api/suppliers/me/tours/
   ```

2. **Upload Main Image:**
   ```bash
   PATCH /api/suppliers/me/tours/1/
   Content-Type: multipart/form-data
   main_image: <file>
   ```

3. **Add Itinerary Items:**
   ```bash
   POST /api/suppliers/me/tours/1/itinerary/
   # Repeat for each day
   ```

4. **Upload Gallery Images:**
   ```bash
   POST /api/suppliers/me/tours/1/images/
   # Repeat for each image
   ```

5. **Add Tour Dates:**
   ```bash
   POST /api/suppliers/me/tours/1/dates/
   # Repeat for each departure date
   ```

6. **Upload Itinerary PDF (optional):**
   ```bash
   PATCH /api/suppliers/me/tours/1/
   Content-Type: multipart/form-data
   itinerary_pdf: <file>
   ```

---

## Support

For issues or questions, please contact the development team or refer to the main API documentation.

