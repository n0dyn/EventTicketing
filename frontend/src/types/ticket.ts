import { Event } from './event';

// Enum for discount types
export enum DiscountType {
  PERCENTAGE = 'percentage',
  FIXED = 'fixed'
}

// Ticket Type
export interface TicketType {
  id: string;
  eventId: string;
  name: string;
  description?: string;
  price: number;
  quantityAvailable: number;
  isActive: boolean;
  saleStartDate?: string;
  saleEndDate?: string;
  minPerOrder: number;
  maxPerOrder?: number;
  visibility: boolean;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
  priceTiers?: PriceTier[];
}

export interface TicketTypeCreate {
  name: string;
  description?: string;
  price: number;
  quantityAvailable: number;
  isActive?: boolean;
  saleStartDate?: string;
  saleEndDate?: string;
  minPerOrder?: number;
  maxPerOrder?: number;
  visibility?: boolean;
  sortOrder?: number;
}

export interface TicketTypeUpdate {
  name?: string;
  description?: string;
  price?: number;
  quantityAvailable?: number;
  isActive?: boolean;
  saleStartDate?: string;
  saleEndDate?: string;
  minPerOrder?: number;
  maxPerOrder?: number;
  visibility?: boolean;
  sortOrder?: number;
}

// Price Tier
export interface PriceTier {
  id: string;
  ticketTypeId: string;
  name: string;
  price: number;
  startDate: string;
  endDate: string;
  quantityAvailable?: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface PriceTierCreate {
  name: string;
  price: number;
  startDate: string;
  endDate: string;
  quantityAvailable?: number;
  isActive?: boolean;
}

export interface PriceTierUpdate {
  name?: string;
  price?: number;
  startDate?: string;
  endDate?: string;
  quantityAvailable?: number;
  isActive?: boolean;
}

// Promo Code
export interface PromoCode {
  id: string;
  eventId: string;
  code: string;
  description?: string;
  discountType: DiscountType;
  discountAmount: number;
  startDate?: string;
  endDate?: string;
  usageLimit?: number;
  usageCount: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  ticketTypes?: TicketType[];
}

export interface PromoCodeCreate {
  code: string;
  description?: string;
  discountType: DiscountType;
  discountAmount: number;
  startDate?: string;
  endDate?: string;
  usageLimit?: number;
  isActive?: boolean;
  ticketTypeIds?: string[];
}

export interface PromoCodeUpdate {
  code?: string;
  description?: string;
  discountType?: DiscountType;
  discountAmount?: number;
  startDate?: string;
  endDate?: string;
  usageLimit?: number;
  isActive?: boolean;
  ticketTypeIds?: string[];
}

// Ticket
export interface Ticket {
  id: string;
  ticketTypeId: string;
  orderId?: string;
  attendeeId?: string;
  code: string;
  pricePaid: number;
  promoCodeId?: string;
  isUsed: boolean;
  usedAt?: string;
  createdAt: string;
  updatedAt: string;
  ticketType?: TicketType;
  promoCode?: PromoCode;
}

export interface TicketCreate {
  code: string;
  pricePaid?: number;
  isUsed?: boolean;
  usedAt?: string;
  promoCodeId?: string;
}

export interface TicketUpdate {
  code?: string;
  isUsed?: boolean;
  usedAt?: string;
}

// Promo Code Validation
export interface PromoCodeValidation {
  code: string;
  eventId: string;
}

export interface PromoCodeValidationResponse {
  isValid: boolean;
  promoCode?: PromoCode;
  message?: string;
} 