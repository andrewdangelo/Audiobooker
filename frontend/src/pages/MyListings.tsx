/**
 * MyListings Page
 * 
 * Shows all store listings created by the current user.
 * Allows publishers to manage their published audiobooks.
 * 
 * @author Andrew D'Angelo
 */

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { PermissionGate } from '@/components/common/PermissionGate';
import { Permission } from '@/types/permissions';
import { StoreListing } from '@/types/storeListing';
import { 
  Search, 
  Plus, 
  Edit, 
  Trash2, 
  Eye, 
  EyeOff, 
  TrendingUp,
  DollarSign,
  Star
} from 'lucide-react';

const MyListings = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // TODO: API Integration - Fetch User's Listings
  // GET /api/v1/store/listings/my-listings
  // Response: StoreListing[]

  // Mock data for demonstration
  const mockListings: StoreListing[] = [
    {
      id: '1',
      audiobookId: 'ab1',
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      narrator: 'Jake Gyllenhaal',
      publisher: 'Scribner',
      description: 'A story of decadence and excess...',
      synopsis: 'Set in the Jazz Age...',
      language: 'en',
      duration: 14400,
      genre: 'Fiction',
      categories: ['Classic', 'Bestseller'],
      tags: ['1920s', 'romance', 'tragedy'],
      publishedYear: 1925,
      price: 12.99,
      currency: 'USD',
      isFree: false,
      status: 'published',
      isPublic: true,
      createdBy: 'user1',
      createdAt: '2025-01-01T00:00:00Z',
      updatedAt: '2025-01-15T00:00:00Z',
      publishedAt: '2025-01-10T00:00:00Z',
      totalSales: 245,
      rating: 4.7,
      reviewCount: 89,
    },
    {
      id: '2',
      audiobookId: 'ab2',
      title: 'To Kill a Mockingbird',
      author: 'Harper Lee',
      description: 'A gripping tale...',
      synopsis: 'In the Deep South...',
      language: 'en',
      duration: 12600,
      genre: 'Fiction',
      categories: ['Classic'],
      tags: ['justice', 'coming-of-age'],
      publishedYear: 1960,
      price: 14.99,
      currency: 'USD',
      isFree: false,
      status: 'pending_review',
      isPublic: false,
      createdBy: 'user1',
      createdAt: '2025-02-01T00:00:00Z',
      updatedAt: '2025-02-01T00:00:00Z',
      totalSales: 0,
    },
    {
      id: '3',
      audiobookId: 'ab3',
      title: '1984',
      author: 'George Orwell',
      description: 'Dystopian masterpiece...',
      synopsis: 'In a totalitarian future...',
      language: 'en',
      duration: 11700,
      genre: 'Science Fiction & Fantasy',
      categories: ['Classic'],
      tags: ['dystopia', 'politics'],
      publishedYear: 1949,
      price: 11.99,
      currency: 'USD',
      isFree: false,
      status: 'draft',
      isPublic: false,
      createdBy: 'user1',
      createdAt: '2025-02-10T00:00:00Z',
      updatedAt: '2025-02-10T00:00:00Z',
      totalSales: 0,
    },
  ];

  const getStatusBadge = (status: StoreListing['status']) => {
    const variants: Record<StoreListing['status'], { variant: any; label: string }> = {
      draft: { variant: 'secondary', label: 'Draft' },
      pending_review: { variant: 'default', label: 'Pending Review' },
      published: { variant: 'default', label: 'Published' },
      unlisted: { variant: 'outline', label: 'Unlisted' },
      rejected: { variant: 'destructive' as any, label: 'Rejected' },
    };
    const config = variants[status];
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  const filteredListings = mockListings.filter(listing => {
    const matchesSearch = listing.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         listing.author.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || listing.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <PermissionGate 
      permission={Permission.PUBLISH_AUDIOBOOK}
      showUpgradePrompt={true}
    >
      <div className="container max-w-6xl py-6 px-4 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">My Listings</h1>
            <p className="text-muted-foreground">
              Manage your published audiobooks
            </p>
          </div>
          <Button asChild>
            <Link to="/library">
              <Plus className="h-4 w-4 mr-2" />
              New Listing
            </Link>
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid md:grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Sales</p>
                  <p className="text-2xl font-bold">245</p>
                </div>
                <TrendingUp className="h-8 w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Revenue</p>
                  <p className="text-2xl font-bold">$3,182.55</p>
                </div>
                <DollarSign className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Avg. Rating</p>
                  <p className="text-2xl font-bold">4.7</p>
                </div>
                <Star className="h-8 w-8 text-yellow-600" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by title or author..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="published">Published</SelectItem>
                  <SelectItem value="pending_review">Pending Review</SelectItem>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="unlisted">Unlisted</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Listings */}
        <div className="space-y-4">
          {filteredListings.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground">No listings found</p>
              </CardContent>
            </Card>
          ) : (
            filteredListings.map(listing => (
              <Card key={listing.id}>
                <CardContent className="pt-6">
                  <div className="flex gap-4">
                    {/* Cover Image */}
                    <div className="flex-shrink-0">
                      {listing.coverImageUrl ? (
                        <img 
                          src={listing.coverImageUrl} 
                          alt={listing.title}
                          className="w-24 h-32 object-cover rounded"
                        />
                      ) : (
                        <div className="w-24 h-32 bg-muted rounded flex items-center justify-center">
                          <span className="text-xs text-muted-foreground">No cover</span>
                        </div>
                      )}
                    </div>

                    {/* Details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="text-lg font-semibold truncate">
                              {listing.title}
                            </h3>
                            {getStatusBadge(listing.status)}
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">
                            by {listing.author}
                            {listing.narrator && ` • Narrated by ${listing.narrator}`}
                          </p>
                          <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
                            {listing.synopsis}
                          </p>
                          <div className="flex flex-wrap gap-2">
                            <Badge variant="outline">{listing.genre}</Badge>
                            {listing.categories.map(cat => (
                              <Badge key={cat} variant="secondary">{cat}</Badge>
                            ))}
                          </div>
                        </div>

                        {/* Stats & Actions */}
                        <div className="flex flex-col items-end gap-2">
                          <div className="text-right">
                            <p className="text-2xl font-bold">
                              {listing.isFree ? 'FREE' : `$${listing.price}`}
                            </p>
                            {listing.status === 'published' && (
                              <>
                                <p className="text-xs text-muted-foreground">
                                  {listing.totalSales || 0} sales
                                </p>
                                {listing.rating && (
                                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                                    <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                                    {listing.rating} ({listing.reviewCount})
                                  </p>
                                )}
                              </>
                            )}
                          </div>
                          <div className="flex gap-2">
                            <Button size="sm" variant="outline" asChild>
                              <Link to={`/publish/${listing.audiobookId}`}>
                                <Edit className="h-4 w-4" />
                              </Link>
                            </Button>
                            <Button size="sm" variant="outline">
                              {listing.isPublic ? (
                                <Eye className="h-4 w-4" />
                              ) : (
                                <EyeOff className="h-4 w-4" />
                              )}
                            </Button>
                            <Button size="sm" variant="outline">
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </PermissionGate>
  );
};

export default MyListings;
