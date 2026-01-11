# Trello-Style Itinerary Board Feature - Architecture Proposal

## Overview
A collaborative, visual itinerary sharing system where each tour/trip can have a shareable board (like Trello) that displays the itinerary in an interactive, card-based format. This allows travelers, suppliers, and resellers to view and interact with trip details in a modern, intuitive interface.

## Key Requirements
- ✅ New database models (separate from existing itinerary text field)
- ✅ Publicly accessible (can be viewed by anyone with a link)
- ✅ Supports every trip/booking
- ✅ Trello-style board interface (cards, columns, drag-and-drop)
- ✅ Rich content (images, text, attachments, checklists)

---

## Database Architecture

### 1. ItineraryBoard Model
**Purpose**: Main board container for each tour/booking

```python
class ItineraryBoard(models.Model):
    """
    A board represents an itinerary for a specific tour package or booking.
    Can be linked to:
    - TourPackage (template/reference itinerary for all bookings)
    - Booking (specific itinerary for a particular booking/group)
    """
    
    # Link to tour or booking (one or the other, not both)
    tour_package = models.ForeignKey(
        'travel.TourPackage',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='itinerary_boards',
        help_text="If linked to tour package, serves as template for all bookings"
    )
    booking = models.ForeignKey(
        'travel.Booking',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='itinerary_boards',
        help_text="If linked to booking, serves as specific itinerary for that trip"
    )
    
    # Board metadata
    title = models.CharField(max_length=255, help_text="Board title (e.g., '5D4N China Tour - Jan 2024')")
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True, db_index=True, help_text="URL-friendly identifier")
    
    # Visibility & Access
    is_public = models.BooleanField(
        default=True,
        help_text="If True, board is publicly accessible via shareable link"
    )
    share_token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique token for sharing (auto-generated)"
    )
    
    # Permissions
    allow_editing = models.BooleanField(
        default=False,
        help_text="Allow public editing (or read-only for public, edit for owners)"
    )
    created_by = models.ForeignKey(
        'account.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_itinerary_boards'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(tour_package__isnull=False) & models.Q(booking__isnull=True) |
                    models.Q(tour_package__isnull=True) & models.Q(booking__isnull=False)
                ),
                name='itinerary_board_must_link_to_tour_or_booking'
            )
        ]
        indexes = [
            models.Index(fields=['tour_package', 'is_public']),
            models.Index(fields=['booking', 'is_public']),
            models.Index(fields=['share_token']),
            models.Index(fields=['slug']),
        ]
```

### 2. ItineraryColumn Model
**Purpose**: Columns/lists on the board (like Trello lists: "Day 1", "Day 2", "Activities", etc.)

```python
class ItineraryColumn(models.Model):
    """
    Columns represent groupings of cards (e.g., "Day 1", "Day 2", "Activities", "Important Info").
    Similar to Trello lists.
    """
    
    board = models.ForeignKey(
        ItineraryBoard,
        on_delete=models.CASCADE,
        related_name='columns'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order (lower = first)")
    color = models.CharField(
        max_length=7,
        default='#0079bf',
        help_text="Hex color code for column header"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['board', 'order']),
        ]
```

### 3. ItineraryCard Model
**Purpose**: Individual cards within columns (activities, notes, locations, etc.)

```python
class ItineraryCard(models.Model):
    """
    Cards represent individual items/activities in the itinerary.
    Can contain rich content: text, images, attachments, checklists, locations, times.
    """
    
    column = models.ForeignKey(
        ItineraryColumn,
        on_delete=models.CASCADE,
        related_name='cards'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Time/Date information
    start_time = models.TimeField(null=True, blank=True, help_text="Activity start time")
    end_time = models.TimeField(null=True, blank=True, help_text="Activity end time")
    date = models.DateField(null=True, blank=True, help_text="Specific date (if different from column context)")
    
    # Location
    location_name = models.CharField(max_length=255, blank=True)
    location_address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Visual
    cover_image = models.ImageField(
        upload_to='itinerary/card_covers/',
        null=True,
        blank=True
    )
    color = models.CharField(max_length=7, blank=True, help_text="Card accent color")
    
    # Ordering
    order = models.PositiveIntegerField(default=0, help_text="Position within column")
    
    # Metadata
    created_by = models.ForeignKey(
        'account.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['column', 'order']),
            models.Index(fields=['date', 'start_time']),
        ]
```

### 4. ItineraryCardAttachment Model
**Purpose**: Attachments on cards (PDFs, images, documents)

```python
class ItineraryCardAttachment(models.Model):
    """Attachments for cards (PDFs, images, documents)"""
    
    card = models.ForeignKey(
        ItineraryCard,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='itinerary/attachments/')
    name = models.CharField(max_length=255, help_text="Display name")
    file_type = models.CharField(
        max_length=50,
        help_text="MIME type or file extension"
    )
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
```

### 5. ItineraryCardChecklist Model
**Purpose**: Checklists within cards (like Trello checklists)

```python
class ItineraryCardChecklist(models.Model):
    """Checklist items for cards"""
    
    card = models.ForeignKey(
        ItineraryCard,
        on_delete=models.CASCADE,
        related_name='checklists'
    )
    title = models.CharField(max_length=255, default="Checklist")
    items = models.JSONField(
        default=list,
        help_text="List of {text: str, completed: bool, id: str} objects"
    )
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'id']
```

### 6. ItineraryCardComment Model (Optional - for collaboration)
**Purpose**: Comments on cards for collaboration

```python
class ItineraryCardComment(models.Model):
    """Comments on cards"""
    
    card = models.ForeignKey(
        ItineraryCard,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(
        'account.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
```

---

## API Design

### Public Endpoints (No Authentication Required)
```
GET  /api/public/itinerary-boards/{share_token}/        # Get board by share token
GET  /api/public/itinerary-boards/{slug}/               # Get board by slug
GET  /api/public/tours/{tour_id}/itinerary-board/       # Get board for tour
GET  /api/public/bookings/{booking_id}/itinerary-board/ # Get board for booking
```

### Authenticated Endpoints
```
# Board Management
GET    /api/itinerary/boards/                           # List user's boards
POST   /api/itinerary/boards/                           # Create board
GET    /api/itinerary/boards/{id}/                      # Get board details
PATCH  /api/itinerary/boards/{id}/                      # Update board
DELETE /api/itinerary/boards/{id}/                      # Delete board
POST   /api/itinerary/boards/{id}/generate-share-link/  # Generate share token

# Column Management
POST   /api/itinerary/boards/{board_id}/columns/        # Create column
PATCH  /api/itinerary/columns/{id}/                     # Update column
DELETE /api/itinerary/columns/{id}/                     # Delete column
POST   /api/itinerary/columns/{id}/reorder/             # Reorder columns

# Card Management
POST   /api/itinerary/columns/{column_id}/cards/        # Create card
GET    /api/itinerary/cards/{id}/                       # Get card details
PATCH  /api/itinerary/cards/{id}/                       # Update card
DELETE /api/itinerary/cards/{id}/                       # Delete card
POST   /api/itinerary/cards/{id}/move/                  # Move card to different column
POST   /api/itinerary/cards/{id}/reorder/               # Reorder cards

# Attachments
POST   /api/itinerary/cards/{card_id}/attachments/      # Upload attachment
DELETE /api/itinerary/attachments/{id}/                 # Delete attachment

# Checklists
POST   /api/itinerary/cards/{card_id}/checklists/       # Create checklist
PATCH  /api/itinerary/checklists/{id}/                  # Update checklist
DELETE /api/itinerary/checklists/{id}/                  # Delete checklist
```

---

## Access Control Strategy

### Public Access (is_public=True)
- **View**: Anyone with share link/token can view
- **Edit**: Only if `allow_editing=True` (or require authentication for editing)

### Authenticated Access
- **Suppliers**: Can create/edit boards for their tour packages
- **Resellers**: Can create/edit boards for their bookings
- **Admins**: Full access to all boards

### Permission Logic
```python
def can_edit_board(user, board):
    if not board.is_public and not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    if board.created_by == user:
        return True
    if board.tour_package and board.tour_package.supplier.user == user:
        return True
    if board.booking and board.booking.reseller.user == user:
        return True
    if board.is_public and board.allow_editing:
        return True  # Public editing enabled
    return False
```

---

## Integration Points

### 1. Auto-create Board from Tour Package
When a tour package is created, optionally create a default board with:
- Columns: "Day 1", "Day 2", ..., "Day N", "Important Info"
- Cards populated from the existing `itinerary` text field (parse by day)

### 2. Auto-create Board from Booking
When a booking is confirmed:
- Optionally create a board linked to that booking
- Copy/initialize from the tour package's board (if exists)

### 3. Sync with Existing Itinerary
- Keep `TourPackage.itinerary` (TextField) as fallback/export
- Board becomes the primary visual interface
- Option to export board back to text format

---

## Frontend Implementation Suggestions

### Tech Stack
- **Board UI**: Use a drag-and-drop library like:
  - `@dnd-kit/core` + `@dnd-kit/sortable` (modern, accessible)
  - `react-beautiful-dnd` (popular, but deprecated)
  - `react-dnd` (flexible, more setup)
- **Card UI**: Custom components with rich text editor (e.g., `tiptap`, `slate`, or `draft-js`)
- **Real-time Updates**: WebSockets (optional) or polling for collaborative editing

### Key Components
```
/itinerary/[shareToken]/page.tsx          # Public board view
/itinerary/[slug]/page.tsx                # Public board by slug
/app/itinerary/boards/page.tsx            # User's boards list
/app/itinerary/boards/[id]/edit/page.tsx  # Board editor
/components/itinerary/
  - BoardView.tsx                         # Main board container
  - Column.tsx                            # Column/list component
  - Card.tsx                              # Card component
  - CardDetailModal.tsx                   # Card detail/edit modal
  - CardAttachment.tsx                    # Attachment display
  - CardChecklist.tsx                     # Checklist component
```

---

## Migration Strategy

### Phase 1: Core Models & API
1. Create models (ItineraryBoard, Column, Card, Attachment, Checklist)
2. Create migrations
3. Build basic CRUD APIs
4. Add permissions

### Phase 2: Public Access
1. Implement share token generation
2. Create public endpoints
3. Add slug support

### Phase 3: Frontend
1. Build board view component
2. Implement drag-and-drop
3. Add card detail modal
4. Implement attachment uploads

### Phase 4: Integration
1. Auto-create boards from tour packages
2. Link boards to bookings
3. Import existing itinerary text to boards

### Phase 5: Enhancement
1. Real-time collaboration (WebSockets)
2. Comments feature
3. Activity feed
4. Board templates

---

## Database Considerations

### New Django App
Create a new app: `itinerary` or `itinerary_boards`

```
travel-marketplace-backend/
  itinerary/  (or itinerary_boards/)
    __init__.py
    models.py
    serializers.py
    views.py
    urls.py
    admin.py
    migrations/
```

### Performance
- Index on `share_token`, `slug`, `tour_package`, `booking`
- Use `select_related` and `prefetch_related` for nested queries
- Consider caching for public boards
- Pagination for cards if columns get very large

---

## Example Usage Flow

### Scenario 1: Supplier creates board for tour package
1. Supplier navigates to tour package detail
2. Clicks "Create Itinerary Board"
3. System creates board linked to tour package
4. System auto-creates columns: "Day 1", "Day 2", etc. (based on tour.days)
5. Supplier adds cards to each column
6. Supplier generates share link and shares with resellers/travelers

### Scenario 2: Traveler views shared board
1. Traveler receives share link (e.g., `/itinerary/abc123xyz/`)
2. Opens link (no login required if public)
3. Views board with all itinerary details
4. Can check off checklist items (if editing allowed)
5. Can view attachments, locations on map, etc.

### Scenario 3: Reseller creates board for booking
1. Reseller creates booking
2. System auto-creates board from tour package template (if exists)
3. Reseller customizes board for their specific booking group
4. Reseller shares board link with their customers

---

## Security Considerations

1. **Share Token**: Use cryptographically secure random token (32+ characters)
2. **File Uploads**: Validate file types, sizes, scan for malware
3. **Rate Limiting**: Prevent abuse of public endpoints
4. **CORS**: Configure CORS for public endpoints if needed
5. **Input Validation**: Sanitize user input, prevent XSS
6. **Permissions**: Always check permissions server-side

---

## Next Steps

1. ✅ Review this proposal
2. ⬜ Decide on database app name (`itinerary` vs `itinerary_boards`)
3. ⬜ Create models in new app
4. ⬜ Create migrations
5. ⬜ Build serializers
6. ⬜ Build API views
7. ⬜ Add URL routing
8. ⬜ Test API endpoints
9. ⬜ Build frontend components
10. ⬜ Integrate with existing tour/booking flows

