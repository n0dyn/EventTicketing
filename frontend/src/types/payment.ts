// Payment Status Enum
export enum PaymentStatus {
  PENDING = 'pending',
  SUCCEEDED = 'succeeded',
  FAILED = 'failed',
  CANCELED = 'canceled',
  REFUNDED = 'refunded',
  PARTIALLY_REFUNDED = 'partially_refunded'
}

// Base Payment Interface
export interface Payment {
  id: string;
  orderId: string;
  amount: number; // Amount in cents
  currency: string;
  status: PaymentStatus;
  stripePaymentIntentId?: string;
  stripeCustomerId?: string;
  paymentMethodId?: string;
  description?: string;
  metadata?: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

// Payment Creation Request
export interface PaymentIntentCreate {
  orderId: string;
  amount: number;
  currency?: string;
  description?: string;
  metadata?: Record<string, any>;
}

// Payment Intent Response
export interface PaymentIntentResponse {
  clientSecret: string;
  paymentIntentId: string;
  payment: Payment;
}

// Payment Confirmation Request
export interface PaymentConfirmation {
  paymentIntentId: string;
  paymentMethodId?: string;
}

// Refund Interface
export interface Refund {
  id: string;
  paymentId: string;
  amount: number; // Amount in cents
  reason?: string;
  stripeRefundId?: string;
  status: PaymentStatus;
  metadata?: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

// Refund Creation Request
export interface RefundCreate {
  amount?: number; // If not provided, refunds full amount
  reason?: string;
  metadata?: Record<string, any>;
}

// Payment Configuration
export interface PaymentConfig {
  stripePublishableKey: string;
  currency: string;
  supportedPaymentMethods: string[];
}

// Payment Webhook Event
export interface PaymentWebhook {
  id: string;
  stripeEventId: string;
  eventType: string;
  processed: boolean;
  payload: Record<string, any>;
  processingError?: string;
  createdAt: string;
  updatedAt: string;
}

// Payment Attempt
export interface PaymentAttempt {
  id: string;
  paymentId: string;
  stripePaymentIntentId?: string;
  status: PaymentStatus;
  failureReason?: string;
  failureCode?: string;
  createdAt: string;
}

// Stripe Elements Types
export interface StripeElementsConfig {
  clientSecret: string;
  appearance?: {
    theme?: 'stripe' | 'night' | 'flat';
    variables?: Record<string, string>;
  };
}

// Payment Form Data
export interface PaymentFormData {
  email: string;
  name: string;
  address?: {
    line1: string;
    line2?: string;
    city: string;
    state: string;
    postal_code: string;
    country: string;
  };
  phone?: string;
}

// Payment confirmation response
export interface PaymentConfirmResponse {
  paymentIntentId: string;
  status: string;
  amountReceived: number;
  currency: string;
  paymentMethod: string;
  receiptUrl?: string;
  order?: {
    id: string;
    eventTitle: string;
    eventDate?: string;
    eventLocation?: string;
    tickets?: {
      ticketTypeName: string;
      quantity: number;
      price: number;
    }[];
  };
} 