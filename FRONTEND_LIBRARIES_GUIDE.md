# Frontend Libraries Guide for Trello-Style Itinerary Board

## ✅ Already Installed (Perfect Choice!)

Your project already has **the best free libraries** for building a Trello-style board:

### 1. **@dnd-kit** (Drag & Drop) ⭐ RECOMMENDED
**Status**: ✅ Already installed
**Packages**:
- `@dnd-kit/core` (^6.3.1)
- `@dnd-kit/sortable` (^10.0.0)
- `@dnd-kit/modifiers` (^9.0.0)
- `@dnd-kit/utilities` (^3.2.2)

**Why it's perfect:**
- ✅ **Free & Open Source** (MIT License)
- ✅ **Modern & Maintained** (actively developed)
- ✅ **Accessible** (built with accessibility in mind)
- ✅ **Performance** (optimized, supports virtual scrolling)
- ✅ **TypeScript** support
- ✅ **React 19 compatible** (you're using React 19.2.0)
- ✅ **Mobile-friendly** (touch support)
- ✅ **Flexible** (supports complex drag patterns)

**Documentation**: https://docs.dndkit.com/
**Example Usage**: You already use it in `data-table.tsx` - perfect reference!

### 2. **TipTap** (Rich Text Editor)
**Status**: ✅ Already installed
**Packages**:
- `@tiptap/react` (^2.27.2)
- `@tiptap/starter-kit`
- `@tiptap/extension-image`
- `@tiptap/extension-link`
- `@tiptap/extension-table`
- Plus table extensions

**Why it's perfect:**
- ✅ **Free & Open Source** (MIT License)
- ✅ **Headless** (you control the UI)
- ✅ **Extensible** (plugin system)
- ✅ **Modern** (ProseMirror based)
- ✅ **Already integrated** in your `rich-text-editor.tsx`

**Use for**: Card descriptions, notes, rich content editing

**Documentation**: https://tiptap.dev/

### 3. **Radix UI / shadcn/ui** (UI Components)
**Status**: ✅ Already installed via shadcn/ui
**Components you can use**:
- Dialog (for card detail modal)
- Popover (for quick actions)
- Dropdown Menu (for card actions)
- Checkbox (for checklists)
- Avatar (for user indicators)
- Separator (for visual division)
- Tabs (if needed)
- Toast/Sonner (for notifications)

**Why it's perfect:**
- ✅ **Free & Open Source** (MIT/Apache 2.0)
- ✅ **Accessible** (ARIA compliant)
- ✅ **Unstyled** (you style with Tailwind)
- ✅ **Already in your project**

---

## 🎯 Recommended Additional Free Libraries

### Optional Enhancements (All Free)

#### 1. **@dnd-kit/sortable** (Already have it!)
You have this, but make sure you're using it for the board:
- Sortable columns (lists)
- Sortable cards within columns
- Cross-column dragging

#### 2. **react-map-gl** or **Leaflet** (For Location Display)
**Purpose**: Display locations on cards (maps)
**Option A**: `react-map-gl` (Mapbox)
```bash
npm install react-map-gl mapbox-gl
```
- ✅ Free tier available
- ✅ Modern, React-friendly
- ⚠️ Requires Mapbox API key (free tier: 50k requests/month)

**Option B**: `react-leaflet` (OpenStreetMap)
```bash
npm install react-leaflet leaflet
```
- ✅ Completely free (no API key needed)
- ✅ Uses OpenStreetMap
- ✅ Good for basic maps

**Recommendation**: Use `react-leaflet` if you want zero cost, or `react-map-gl` if you need better styling/features.

#### 3. **react-hook-form** (Already have it!)
✅ You already have this - perfect for card forms, checklist management

#### 4. **date-fns** (Already have it!)
✅ You already have this - perfect for formatting dates/times on cards

#### 5. **zod** (Already have it!)
✅ You already have this - perfect for form validation

---

## 📦 Implementation Strategy

### Core Board Component Structure

```typescript
// components/itinerary/Board.tsx
"use client"

import { DndContext, DragEndEvent, DragStartEvent } from "@dnd-kit/core"
import { SortableContext, horizontalListSortingStrategy } from "@dnd-kit/sortable"
import { useMemo } from "react"

// Board container with horizontal scrolling columns
export function ItineraryBoard({ board, columns, cards }) {
  const sensors = useSensors(
    useSensor(MouseSensor),
    useSensor(TouchSensor),
    useSensor(KeyboardSensor)
  )

  function handleDragEnd(event: DragEndEvent) {
    // Handle card movement between columns
    // Update card.column_id via API
  }

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <div className="flex gap-4 overflow-x-auto p-4">
        <SortableContext
          items={columns.map(c => c.id)}
          strategy={horizontalListSortingStrategy}
        >
          {columns.map(column => (
            <Column key={column.id} column={column} cards={cards.filter(c => c.column_id === column.id)} />
          ))}
        </SortableContext>
      </div>
    </DndContext>
  )
}
```

### Column Component

```typescript
// components/itinerary/Column.tsx
"use client"

import { useSortable } from "@dnd-kit/sortable"
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"

export function Column({ column, cards }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: column.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="min-w-[300px] bg-muted rounded-lg p-4"
    >
      <div {...attributes} {...listeners} className="flex items-center gap-2 mb-4">
        <h3 className="font-semibold">{column.title}</h3>
        <span className="text-sm text-muted-foreground">{cards.length}</span>
      </div>
      
      <SortableContext items={cards.map(c => c.id)} strategy={verticalListSortingStrategy}>
        <div className="space-y-2">
          {cards.map(card => (
            <Card key={card.id} card={card} />
          ))}
        </div>
      </SortableContext>
    </div>
  )
}
```

### Card Component

```typescript
// components/itinerary/Card.tsx
"use client"

import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { Dialog, DialogTrigger } from "@/components/ui/dialog"
import { Card as UICard } from "@/components/ui/card"

export function Card({ card }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: card.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        <div
          ref={setNodeRef}
          style={style}
          {...attributes}
          {...listeners}
          className="cursor-grab active:cursor-grabbing"
        >
          <UICard className="p-3 hover:shadow-md transition-shadow">
            {card.cover_image && (
              <img src={card.cover_image} alt={card.title} className="w-full h-32 object-cover rounded mb-2" />
            )}
            <h4 className="font-medium">{card.title}</h4>
            {card.description && (
              <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                {card.description}
              </p>
            )}
            {card.start_time && (
              <p className="text-xs text-muted-foreground mt-2">
                {card.start_time} - {card.end_time}
              </p>
            )}
          </UICard>
        </div>
      </DialogTrigger>
      <CardDetailModal card={card} />
    </Dialog>
  )
}
```

### Card Detail Modal (with TipTap)

```typescript
// components/itinerary/CardDetailModal.tsx
"use client"

import { DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { RichTextEditor } from "@/components/ui/rich-text-editor"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"

export function CardDetailModal({ card }) {
  return (
    <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle>
          <Input defaultValue={card.title} />
        </DialogTitle>
      </DialogHeader>
      
      <div className="space-y-4 mt-4">
        {/* Rich text description */}
        <div>
          <label className="text-sm font-medium">Description</label>
          <RichTextEditor
            value={card.description}
            onChange={(value) => {/* Update card */}}
            placeholder="Add a description..."
          />
        </div>

        {/* Time/Date inputs */}
        <div className="grid grid-cols-2 gap-4">
          <Input type="time" label="Start Time" />
          <Input type="time" label="End Time" />
        </div>

        {/* Location */}
        <Input label="Location" placeholder="Enter location" />

        {/* Checklist */}
        <div>
          <label className="text-sm font-medium mb-2 block">Checklist</label>
          {card.checklists?.map(item => (
            <div key={item.id} className="flex items-center gap-2">
              <Checkbox checked={item.completed} />
              <span>{item.text}</span>
            </div>
          ))}
        </div>

        {/* Attachments */}
        <div>
          <label className="text-sm font-medium mb-2 block">Attachments</label>
          {/* File upload component */}
        </div>
      </div>
    </DialogContent>
  )
}
```

---

## 🎨 Styling Recommendations

You're using **Tailwind CSS** (perfect!) - here are some styling tips:

### Board Container
```tsx
<div className="flex gap-4 overflow-x-auto p-4 bg-background min-h-screen">
  {/* Columns */}
</div>
```

### Column Styling
```tsx
<div className="min-w-[300px] max-w-[300px] bg-muted/50 rounded-lg p-4 flex flex-col">
  {/* Column header */}
  {/* Cards */}
</div>
```

### Card Styling
```tsx
<div className="bg-card border rounded-lg p-3 shadow-sm hover:shadow-md transition-shadow cursor-grab active:cursor-grabbing">
  {/* Card content */}
</div>
```

---

## 📚 Useful Resources

### @dnd-kit Examples
- Official Examples: https://docs.dndkit.com/examples
- Sortable Examples: https://docs.dndkit.com/presets/sortable/examples
- Multi-container: https://docs.dndkit.com/examples/multiple-containers

### TipTap Examples
- Basic Editor: You already have `rich-text-editor.tsx` - reuse it!
- Card Editor: Use the same component for card descriptions

### shadcn/ui Components
- Dialog: Perfect for card detail modal
- Popover: For quick actions
- Dropdown Menu: For card/column actions
- Checkbox: For checklists
- Input: For card titles, times, locations

---

## 🚀 Quick Start Checklist

- [x] ✅ @dnd-kit/core - Already installed
- [x] ✅ @dnd-kit/sortable - Already installed
- [x] ✅ @dnd-kit/modifiers - Already installed
- [x] ✅ TipTap - Already installed
- [x] ✅ shadcn/ui components - Already installed
- [x] ✅ Tailwind CSS - Already installed
- [ ] ⬜ Create Board component
- [ ] ⬜ Create Column component
- [ ] ⬜ Create Card component
- [ ] ⬜ Create CardDetailModal component
- [ ] ⬜ Implement drag handlers
- [ ] ⬜ Connect to API

---

## 💡 Pro Tips

1. **Reuse your existing components**: You already have drag-and-drop working in `data-table.tsx` - use it as a reference!

2. **Performance**: For large boards, consider virtual scrolling (React Window or TanStack Virtual)

3. **Mobile**: @dnd-kit handles touch automatically, but test on real devices

4. **Accessibility**: @dnd-kit is accessible by default, but add ARIA labels

5. **State Management**: Use React Query (you have it!) for server state, local state for drag preview

6. **Optimistic Updates**: Update UI immediately on drag, sync with API in background

---

## 📦 Summary

**You don't need to install anything new!** Your current stack is perfect:

✅ **Drag & Drop**: @dnd-kit (best in class, already installed)
✅ **Rich Text**: TipTap (modern, extensible, already installed)
✅ **UI Components**: shadcn/ui (accessible, beautiful, already installed)
✅ **Styling**: Tailwind CSS (already installed)
✅ **Forms**: react-hook-form + zod (already installed)
✅ **Icons**: lucide-react (already installed)

**Optional additions** (only if needed):
- `react-leaflet` - For maps (if you want location visualization)
- That's it! Everything else is already there.

---

## 🎯 Next Steps

1. Create the board components using your existing libraries
2. Reference your `data-table.tsx` for drag-and-drop patterns
3. Use your `rich-text-editor.tsx` for card descriptions
4. Style with Tailwind using your existing design system

You're all set! 🚀

