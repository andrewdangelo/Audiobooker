/**
 * PublishToStore Component
 * 
 * Form for publishing an uploaded audiobook to the store.
 * Only accessible by Publisher tier users and Admins.
 * Includes all book metadata, pricing, and publishing options.
 * 
 * @author Andrew D'Angelo
 */

import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { PermissionGate } from '@/components/common/PermissionGate';
import { usePermissions } from '@/hooks/usePermissions';
import { useToast } from '@/hooks/useToast';
import { Permission } from '@/types/permissions';
import { 
  StoreListingCreate, 
  GENRE_OPTIONS, 
  LANGUAGE_OPTIONS, 
  CATEGORY_OPTIONS 
} from '@/types/storeListing';
import { 
  Book, 
  DollarSign, 
  FileText, 
  Image, 
  Tag, 
  Globe, 
  Calendar,
  User,
  Mic,
  Save,
  Eye,
  X,
  Plus
} from 'lucide-react';

const PublishToStore = () => {
  const { audiobookId } = useParams<{ audiobookId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { hasPermission } = usePermissions();
  const [isLoading, setIsLoading] = useState(false);
  const [currentTag, setCurrentTag] = useState('');

  // Form state
  const [formData, setFormData] = useState<Partial<StoreListingCreate>>({
    audiobookId: audiobookId || '',
    title: '',
    author: '',
    narrator: '',
    publisher: '',
    description: '',
    synopsis: '',
    genre: '',
    language: 'en',
    categories: [],
    tags: [],
    isbn: '',
    publishedYear: new Date().getFullYear(),
    edition: '',
    price: 9.99,
    currency: 'USD',
    discountPrice: undefined,
    isFree: false,
  });

  // Update form field
  const updateField = (field: keyof StoreListingCreate, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  // Add tag
  const addTag = () => {
    if (currentTag.trim() && !formData.tags?.includes(currentTag.trim())) {
      updateField('tags', [...(formData.tags || []), currentTag.trim()]);
      setCurrentTag('');
    }
  };

  // Remove tag
  const removeTag = (tagToRemove: string) => {
    updateField('tags', formData.tags?.filter(tag => tag !== tagToRemove) || []);
  };

  // Toggle category
  const toggleCategory = (category: string) => {
    const categories = formData.categories || [];
    if (categories.includes(category)) {
      updateField('categories', categories.filter(c => c !== category));
    } else {
      updateField('categories', [...categories, category]);
    }
  };

  // Handle form submission
  const handleSubmit = async (status: 'draft' | 'pending_review') => {
    setIsLoading(true);

    // Validation
    if (!formData.title || !formData.author || !formData.description || 
        !formData.synopsis || !formData.genre) {
      toast({
        title: "Validation Error",
        description: "Please fill in all required fields.",
        variant: "destructive",
      });
      setIsLoading(false);
      return;
    }

    // TODO: API Integration - Publish to Store
    // POST /api/v1/store/listings
    // Body: { ...formData, status }
    
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      toast({
        title: status === 'draft' ? "Saved as Draft" : "Submitted for Review",
        description: status === 'draft' 
          ? "Your listing has been saved and can be published later."
          : "Your audiobook has been submitted and is pending review.",
      });

      // Navigate to store or library
      navigate('/library');
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to publish audiobook. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <PermissionGate 
      permission={Permission.PUBLISH_AUDIOBOOK}
      showUpgradePrompt={true}
    >
      <div className="container max-w-5xl py-6 px-4 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Publish to Store</h1>
            <p className="text-muted-foreground">
              Add your audiobook to the marketplace
            </p>
          </div>
          <Button variant="outline" onClick={() => navigate(-1)}>
            Cancel
          </Button>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Form */}
          <div className="lg:col-span-2 space-y-6">
            {/* Basic Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Book className="h-5 w-5" />
                  Basic Information
                </CardTitle>
                <CardDescription>
                  Primary details about your audiobook
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-2">
                  <Label htmlFor="title">
                    Title <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="title"
                    value={formData.title}
                    onChange={(e) => updateField('title', e.target.value)}
                    placeholder="The Great Gatsby"
                  />
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="author">
                      Author <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="author"
                      value={formData.author}
                      onChange={(e) => updateField('author', e.target.value)}
                      placeholder="F. Scott Fitzgerald"
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="narrator">Narrator</Label>
                    <Input
                      id="narrator"
                      value={formData.narrator}
                      onChange={(e) => updateField('narrator', e.target.value)}
                      placeholder="Jake Gyllenhaal"
                    />
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="publisher">Publisher</Label>
                    <Input
                      id="publisher"
                      value={formData.publisher}
                      onChange={(e) => updateField('publisher', e.target.value)}
                      placeholder="Scribner"
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="language">Language</Label>
                    <Select 
                      value={formData.language} 
                      onValueChange={(val) => updateField('language', val)}
                    >
                      <SelectTrigger id="language">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {LANGUAGE_OPTIONS.map(lang => (
                          <SelectItem key={lang.value} value={lang.value}>
                            {lang.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Content Details */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Content Details
                </CardTitle>
                <CardDescription>
                  Detailed description and synopsis
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-2">
                  <Label htmlFor="synopsis">
                    Short Synopsis <span className="text-destructive">*</span>
                  </Label>
                  <textarea
                    id="synopsis"
                    className="min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    value={formData.synopsis}
                    onChange={(e) => updateField('synopsis', e.target.value)}
                    placeholder="A brief, compelling summary (150-300 characters)"
                    maxLength={300}
                  />
                  <p className="text-xs text-muted-foreground">
                    {formData.synopsis?.length || 0}/300 characters
                  </p>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="description">
                    Full Description <span className="text-destructive">*</span>
                  </Label>
                  <textarea
                    id="description"
                    className="min-h-[200px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    value={formData.description}
                    onChange={(e) => updateField('description', e.target.value)}
                    placeholder="Detailed description of the audiobook, themes, and what listeners can expect..."
                  />
                </div>
              </CardContent>
            </Card>

            {/* Categorization */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Tag className="h-5 w-5" />
                  Categorization
                </CardTitle>
                <CardDescription>
                  Help readers discover your audiobook
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-2">
                  <Label htmlFor="genre">
                    Genre <span className="text-destructive">*</span>
                  </Label>
                  <Select 
                    value={formData.genre} 
                    onValueChange={(val) => updateField('genre', val)}
                  >
                    <SelectTrigger id="genre">
                      <SelectValue placeholder="Select a genre" />
                    </SelectTrigger>
                    <SelectContent>
                      {GENRE_OPTIONS.map(genre => (
                        <SelectItem key={genre} value={genre}>
                          {genre}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label>Categories</Label>
                  <div className="flex flex-wrap gap-2">
                    {CATEGORY_OPTIONS.map(category => {
                      const isSelected = formData.categories?.includes(category);
                      return (
                        <Badge
                          key={category}
                          variant={isSelected ? "default" : "outline"}
                          className="cursor-pointer"
                          onClick={() => toggleCategory(category)}
                        >
                          {category}
                        </Badge>
                      );
                    })}
                  </div>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="tags">Tags</Label>
                  <div className="flex gap-2">
                    <Input
                      id="tags"
                      value={currentTag}
                      onChange={(e) => setCurrentTag(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                      placeholder="Add tags (press Enter)"
                    />
                    <Button type="button" onClick={addTag} size="icon">
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  {formData.tags && formData.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {formData.tags.map(tag => (
                        <Badge key={tag} variant="secondary">
                          {tag}
                          <X 
                            className="h-3 w-3 ml-1 cursor-pointer" 
                            onClick={() => removeTag(tag)}
                          />
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Publishing Details */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5" />
                  Publishing Details
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="isbn">ISBN</Label>
                    <Input
                      id="isbn"
                      value={formData.isbn}
                      onChange={(e) => updateField('isbn', e.target.value)}
                      placeholder="978-3-16-148410-0"
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="publishedYear">Published Year</Label>
                    <Input
                      id="publishedYear"
                      type="number"
                      value={formData.publishedYear}
                      onChange={(e) => updateField('publishedYear', parseInt(e.target.value))}
                      min="1900"
                      max={new Date().getFullYear()}
                    />
                  </div>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="edition">Edition</Label>
                  <Input
                    id="edition"
                    value={formData.edition}
                    onChange={(e) => updateField('edition', e.target.value)}
                    placeholder="1st Edition, Unabridged"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Pricing */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5" />
                  Pricing
                </CardTitle>
                <CardDescription>
                  Set your audiobook's price
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="isFree"
                    checked={formData.isFree}
                    onChange={(e) => updateField('isFree', e.target.checked)}
                  />
                  <Label htmlFor="isFree" className="font-normal">
                    Offer this audiobook for free
                  </Label>
                </div>

                {!formData.isFree && (
                  <>
                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="grid gap-2">
                        <Label htmlFor="price">
                          Price <span className="text-destructive">*</span>
                        </Label>
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">$</span>
                          <Input
                            id="price"
                            type="number"
                            step="0.01"
                            min="0"
                            value={formData.price}
                            onChange={(e) => updateField('price', parseFloat(e.target.value))}
                          />
                        </div>
                      </div>
                      <div className="grid gap-2">
                        <Label htmlFor="discountPrice">Discount Price (Optional)</Label>
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">$</span>
                          <Input
                            id="discountPrice"
                            type="number"
                            step="0.01"
                            min="0"
                            value={formData.discountPrice || ''}
                            onChange={(e) => updateField('discountPrice', e.target.value ? parseFloat(e.target.value) : undefined)}
                          />
                        </div>
                      </div>
                    </div>

                    {formData.discountPrice && formData.price && formData.discountPrice < formData.price && (
                      <div className="p-3 bg-green-50 dark:bg-green-950 rounded-lg">
                        <p className="text-sm text-green-700 dark:text-green-300">
                          Save {Math.round((1 - formData.discountPrice / formData.price) * 100)}% - 
                          Discount: ${formData.discountPrice.toFixed(2)} (Regular: ${formData.price.toFixed(2)})
                        </p>
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Preview Card */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Publishing Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button 
                  className="w-full" 
                  onClick={() => handleSubmit('pending_review')}
                  disabled={isLoading}
                >
                  <Eye className="h-4 w-4 mr-2" />
                  {isLoading ? 'Publishing...' : 'Publish for Review'}
                </Button>
                <Button 
                  className="w-full" 
                  variant="outline"
                  onClick={() => handleSubmit('draft')}
                  disabled={isLoading}
                >
                  <Save className="h-4 w-4 mr-2" />
                  Save as Draft
                </Button>
              </CardContent>
            </Card>

            {/* Cover Image */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Image className="h-4 w-4" />
                  Cover Image
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {formData.coverImageUrl ? (
                  <img 
                    src={formData.coverImageUrl} 
                    alt="Cover" 
                    className="w-full rounded-lg border"
                  />
                ) : (
                  <div className="aspect-[2/3] w-full rounded-lg border border-dashed flex items-center justify-center bg-muted">
                    <p className="text-sm text-muted-foreground">No cover image</p>
                  </div>
                )}
                <Button variant="outline" size="sm" className="w-full">
                  Upload Cover
                  {/* TODO: API Integration - Upload Cover Image
                      POST /api/v1/store/listings/{id}/cover
                  */}
                </Button>
              </CardContent>
            </Card>

            {/* Publishing Checklist */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Publishing Checklist</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <ChecklistItem 
                  completed={!!formData.title} 
                  text="Title" 
                />
                <ChecklistItem 
                  completed={!!formData.author} 
                  text="Author" 
                />
                <ChecklistItem 
                  completed={!!formData.description && formData.description.length > 50} 
                  text="Description (50+ chars)" 
                />
                <ChecklistItem 
                  completed={!!formData.synopsis && formData.synopsis.length > 20} 
                  text="Synopsis" 
                />
                <ChecklistItem 
                  completed={!!formData.genre} 
                  text="Genre" 
                />
                <ChecklistItem 
                  completed={formData.isFree || (!!formData.price && formData.price > 0)} 
                  text="Price" 
                />
              </CardContent>
            </Card>

            {/* Info */}
            <Card className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
              <CardContent className="pt-6">
                <p className="text-sm text-blue-900 dark:text-blue-100">
                  <strong>Review Process:</strong> After submitting, your audiobook will be reviewed 
                  by our team within 24-48 hours. You'll be notified via email once it's approved.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </PermissionGate>
  );
};

// Checklist item component
const ChecklistItem = ({ completed, text }: { completed: boolean; text: string }) => (
  <div className="flex items-center gap-2 text-sm">
    <div className={`h-4 w-4 rounded-full flex items-center justify-center ${
      completed ? 'bg-green-500' : 'bg-muted'
    }`}>
      {completed && <span className="text-white text-xs">✓</span>}
    </div>
    <span className={completed ? 'text-foreground' : 'text-muted-foreground'}>
      {text}
    </span>
  </div>
);

export default PublishToStore;
