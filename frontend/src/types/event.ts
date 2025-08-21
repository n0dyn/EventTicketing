import { User } from './user';
import { Organization } from './organization';
import { TicketType } from './ticket';

export enum EventStatus {
  DRAFT = 'draft',
  PUBLISHED = 'published',
  CANCELLED = 'cancelled',
  COMPLETED = 'completed'
}

export interface Event {
  id: string;
  title: string;
  slug: string;
  description?: string;
  location?: string;
  venue?: string;
  startTime: string;
  endTime: string;
  timezone: string;
  featuredImage?: string;
  bannerImage?: string;
  capacity?: number;
  price?: number;
  currency: string;
  isFree: boolean;
  status: EventStatus;
  isPublic: boolean;
  ownerId: string;
  organizationId: string;
  createdAt: string;
  updatedAt: string;
  owner?: User;
  organization?: Organization;
  ticketTypes?: TicketType[];
}

export interface EventCreate {
  title: string;
  description?: string;
  location?: string;
  venue?: string;
  startTime: string;
  endTime: string;
  timezone?: string;
  featuredImage?: string;
  bannerImage?: string;
  capacity?: number;
  price?: number;
  currency?: string;
  isFree?: boolean;
  status?: EventStatus;
  isPublic?: boolean;
  organizationId: string;
}

export interface EventUpdate {
  title?: string;
  description?: string;
  location?: string;
  venue?: string;
  startTime?: string;
  endTime?: string;
  timezone?: string;
  featuredImage?: string;
  bannerImage?: string;
  capacity?: number;
  price?: number;
  currency?: string;
  isFree?: boolean;
  status?: EventStatus;
  isPublic?: boolean;
}

export interface EventFilters {
  search?: string;
  organizationId?: string;
  status?: EventStatus;
  startDateAfter?: string;
  startDateBefore?: string;
  isFree?: boolean;
}

export interface EventList {
  items: Event[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Public event interface for public-facing pages
export interface PublicEvent {
  id: string;
  title: string;
  slug: string;
  description?: string;
  location?: string;
  venue_name?: string;
  venue_address?: string;
  start_datetime: string;
  end_datetime: string;
  timezone: string;
  image_url?: string;
  banner_url?: string;
  capacity?: number;
  is_free: boolean;
  status: EventStatus;
  categories?: string[];
  tags?: string[];
  min_price?: number;
  max_price?: number;
  currency: string;
  organization?: {
    id: string;
    name: string;
    logo_url?: string;
  };
  ticket_types?: Array<{
    id: string;
    name: string;
    description?: string;
    price: number;
    quantity: number;
    available: number;
    is_active: boolean;
  }>;
  price_tiers?: Array<{
    id: string;
    name: string;
    price: number;
    description?: string;
  }>;
  promo_codes?: Array<{
    id: string;
    code: string;
    discount_type: 'percentage' | 'fixed';
    discount_value: number;
    valid_until?: string;
    usage_limit?: number;
    usage_count?: number;
  }>;
}

export interface PublicEventList {
  data: PublicEvent[];
  total: number;
  page: number;
  size: number;
}