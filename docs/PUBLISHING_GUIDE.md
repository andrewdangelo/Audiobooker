# Publishing to Store - User Guide

## Overview

The **Publish to Store** feature allows Publisher-tier users and Admins to convert their uploaded audiobooks into store listings that can be purchased by other users.

## Accessing the Feature

### Requirements
- **Permission Required**: `PUBLISH_AUDIOBOOK`
- **Available to**: Publisher, Enterprise, and Admin users
- **Not available to**: Basic and Premium users (upgrade prompt will be shown)

### How to Access
1. Upload an audiobook through the Upload page
2. Once the audiobook is processed, click the **"Publish to Store"** button
3. Alternatively, navigate to `/publish/:audiobookId` directly

## Publishing Form

### Required Fields
These fields must be completed before publishing:

- **Title** - The audiobook's title
- **Author** - Primary author name
- **Description** - Detailed description (minimum 50 characters)
- **Synopsis** - Short summary for preview (20-300 characters)
- **Genre** - Select from 21 genre options
- **Price** - Set price (or mark as free)

### Optional Fields

#### Basic Information
- **Narrator** - Voice actor/narrator name
- **Publisher** - Publishing house or entity
- **Language** - Default: English (10 languages supported)

#### Publishing Details
- **ISBN** - International Standard Book Number
- **Published Year** - Original publication year
- **Edition** - Edition information (e.g., "1st Edition, Unabridged")

#### Categorization
- **Categories** - Select from preset categories (Bestseller, New Release, etc.)
- **Tags** - Custom tags for discoverability

#### Media
- **Cover Image** - Upload custom cover art
- **Sample Audio** - Preview clip for potential buyers

#### Pricing
- **Price** - Base price in USD
- **Discount Price** - Optional sale price
- **Free** - Checkbox to offer for free

## Publishing Workflow

### 1. Draft Mode
Save your listing as a draft to work on it later:
```typescript
// Click "Save as Draft" button
// Status: 'draft'
// Not visible to public
```

### 2. Submit for Review
Submit your completed listing for admin review:
```typescript
// Click "Publish for Review" button
// Status: 'pending_review'
// Reviewed within 24-48 hours
```

### 3. Published
Once approved by admins:
```typescript
// Status: 'published'
// Visible in store
// Available for purchase
```

### 4. Other Statuses
- **Unlisted** - Published but hidden from browse
- **Rejected** - Did not pass review (will receive feedback)

## Using the Components

### PublishButton Component
Add a publish button anywhere in your app:

```typescript
import { PublishButton } from '@/components/common/PublishButton';

function AudiobookCard({ audiobook }) {
  return (
    <div>
      <h3>{audiobook.title}</h3>
      <PublishButton 
        audiobookId={audiobook.id}
        variant="default"
        size="sm"
      />
    </div>
  );
}
```

Props:
- `audiobookId` (required) - The audiobook ID to publish
- `variant` - Button style: 'default' | 'outline' | 'secondary' | 'ghost'
- `size` - Button size: 'default' | 'sm' | 'lg' | 'icon'
- `className` - Additional CSS classes
- `showIcon` - Show/hide store icon (default: true)

### Permission Gating
The publish button automatically checks permissions. Users without PUBLISH_AUDIOBOOK permission will see a disabled button with a lock icon.

## Managing Listings

### My Listings Page
Access at `/my-listings` to:
- View all your store listings
- See sales statistics and revenue
- Edit existing listings
- Toggle public/unlisted status
- Delete listings

### Features
- **Search** - Filter by title or author
- **Status Filter** - View by status (all, published, draft, etc.)
- **Quick Actions** - Edit, toggle visibility, delete
- **Analytics** - Sales count, revenue, ratings

### Statistics Dashboard
View key metrics:
- **Total Sales** - Number of copies sold
- **Total Revenue** - Earnings from sales
- **Average Rating** - User rating (if published)

## API Integration Points

### Create/Update Listing
```typescript
// TODO: Implement in your API
POST /api/v1/store/listings
Body: {
  audiobookId: string,
  title: string,
  author: string,
  description: string,
  synopsis: string,
  genre: string,
  price: number,
  // ... other fields
  status: 'draft' | 'pending_review'
}
```

### Fetch User Listings
```typescript
// TODO: Implement in your API
GET /api/v1/store/listings/my-listings
Response: StoreListing[]
```

### Update Listing
```typescript
// TODO: Implement in your API
PATCH /api/v1/store/listings/:id
Body: Partial<StoreListingUpdate>
```

### Delete Listing
```typescript
// TODO: Implement in your API
DELETE /api/v1/store/listings/:id
```

### Upload Cover Image
```typescript
// TODO: Implement in your API
POST /api/v1/store/listings/:id/cover
Content-Type: multipart/form-data
```

## Best Practices

### Writing Descriptions
- **Synopsis**: 150-300 characters, hook the reader
- **Description**: Detailed overview, what to expect, themes
- Use engaging language
- Highlight unique aspects

### Pricing Strategy
- Research similar audiobooks in your genre
- Consider audiobook length/duration
- Use discount pricing for promotions
- Free audiobooks can build audience

### Categorization
- Choose the most accurate genre
- Select 2-4 relevant categories
- Add 5-10 descriptive tags
- Use popular search terms

### Cover Images
- Recommended: 1600x2400px (2:3 ratio)
- High quality, professional design
- Text should be readable at small sizes
- Follow genre conventions

## Troubleshooting

### Can't See Publish Button
- Check your subscription tier (requires Publisher+)
- Verify audiobook is fully processed
- Ensure you're the audiobook owner

### Listing Rejected
- Review feedback from admin team
- Make required changes
- Resubmit for review

### Sales Not Showing
- Sales data may take 24 hours to update
- Check listing is set to 'published' status
- Verify pricing is set correctly

## Future Enhancements
- [ ] Bulk listing management
- [ ] Advanced analytics dashboard
- [ ] A/B testing for descriptions
- [ ] Automated pricing suggestions
- [ ] Marketing campaign tools
- [ ] Royalty management
- [ ] Multi-author collaboration
