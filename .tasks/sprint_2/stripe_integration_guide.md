# Stripe Integration Guide for Payment Processing

## Overview
This guide provides step-by-step instructions for integrating Stripe payment processing into the EventTicketing platform. It covers both backend and frontend implementation details.

## Prerequisites
- Stripe account (can be created at [stripe.com](https://stripe.com))
- API keys from Stripe Dashboard
- Node.js backend environment
- Next.js frontend

## 1. Stripe Account Setup

### Create and Configure Stripe Account
1. Sign up for a Stripe account at [stripe.com](https://stripe.com)
2. Navigate to the Developers > API keys section
3. Note your publishable key and secret key
4. Create a webhook endpoint in the Stripe Dashboard:
   - Developers > Webhooks > Add endpoint
   - Use your backend URL with the path `/api/webhooks/stripe`
   - Select events to listen for: `payment_intent.succeeded`, `payment_intent.failed`

## 2. Backend Implementation

### Install Dependencies
```bash
# Using npm
npm install stripe

# Using yarn
yarn add stripe
```

### Environment Variables Setup
Create or update your `.env` file with Stripe credentials:
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Create Stripe Client
```typescript
// services/stripe.ts
import Stripe from 'stripe';

if (!process.env.STRIPE_SECRET_KEY) {
  throw new Error('STRIPE_SECRET_KEY is not defined');
}

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, {
  apiVersion: '2023-10-16',
});

export default stripe;
```

### Database Models
Create payment-related models:

```typescript
// models/payment.ts
import { Schema, model, Document, Types } from 'mongoose';
// Or use your preferred ORM

export interface IPayment extends Document {
  userId: Types.ObjectId;
  orderId: Types.ObjectId;
  paymentIntentId: string;
  amount: number;
  currency: string;
  status: 'pending' | 'succeeded' | 'failed' | 'refunded';
  paymentMethod: string;
  createdAt: Date;
  updatedAt: Date;
}

const PaymentSchema = new Schema(
  {
    userId: { type: Schema.Types.ObjectId, ref: 'User', required: true },
    orderId: { type: Schema.Types.ObjectId, ref: 'Order', required: true },
    paymentIntentId: { type: String, required: true, unique: true },
    amount: { type: Number, required: true },
    currency: { type: String, required: true, default: 'usd' },
    status: {
      type: String,
      required: true,
      enum: ['pending', 'succeeded', 'failed', 'refunded'],
      default: 'pending',
    },
    paymentMethod: { type: String },
  },
  { timestamps: true }
);

export default model<IPayment>('Payment', PaymentSchema);
```

### Create Payment Intent Endpoint
```typescript
// api/payment/create-payment-intent.ts
import stripe from '@/services/stripe';

export async function POST(request: Request) {
  try {
    const { amount, currency = 'usd', metadata } = await request.json();

    // Create a PaymentIntent with the order amount and currency
    const paymentIntent = await stripe.paymentIntents.create({
      amount, // amount in smallest currency unit (e.g., cents for USD)
      currency,
      metadata,
      automatic_payment_methods: {
        enabled: true,
      },
    });

    // Save payment intent to database
    // ...

    return Response.json({ clientSecret: paymentIntent.client_secret });
  } catch (error) {
    console.error('Error creating payment intent:', error);
    return Response.json({ error: 'Failed to create payment intent' }, { status: 500 });
  }
}
```

### Implement Webhook Handler
```typescript
// api/webhooks/stripe.ts
import stripe from '@/services/stripe';
import { headers } from 'next/headers';

export async function POST(request: Request) {
  const body = await request.text();
  const signature = headers().get('stripe-signature') || '';

  try {
    const event = stripe.webhooks.constructEvent(
      body,
      signature,
      process.env.STRIPE_WEBHOOK_SECRET!
    );

    switch (event.type) {
      case 'payment_intent.succeeded':
        await handlePaymentIntentSucceeded(event.data.object);
        break;
      case 'payment_intent.failed':
        await handlePaymentIntentFailed(event.data.object);
        break;
      default:
        console.log(`Unhandled event type: ${event.type}`);
    }

    return Response.json({ received: true });
  } catch (err: any) {
    console.error(`Webhook Error: ${err.message}`);
    return Response.json(
      { error: `Webhook Error: ${err.message}` },
      { status: 400 }
    );
  }
}

async function handlePaymentIntentSucceeded(paymentIntent: any) {
  // Update order status
  // Update payment status
  // Generate tickets
  // Send email confirmation
}

async function handlePaymentIntentFailed(paymentIntent: any) {
  // Handle failed payment
  // Update order status
  // Notify customer
}
```

## 3. Frontend Implementation

### Install Dependencies
```bash
# Using npm
npm install @stripe/stripe-js @stripe/react-stripe-js

# Using yarn
yarn add @stripe/stripe-js @stripe/react-stripe-js
```

### Create Stripe Provider
```tsx
// components/payment/StripeProvider.tsx
"use client";

import { Elements } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";
import React from "react";

// Make sure to call `loadStripe` outside of a component's render to avoid
// recreating the `Stripe` object on every render
const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);

export default function StripeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  return <Elements stripe={stripePromise}>{children}</Elements>;
}
```

### Implement Payment Form
```tsx
// components/payment/CheckoutForm.tsx
"use client";

import { useState, useEffect } from "react";
import {
  PaymentElement,
  useStripe,
  useElements
} from "@stripe/react-stripe-js";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export default function CheckoutForm({ 
  amount, 
  orderId 
}: { 
  amount: number;
  orderId: string;
}) {
  const stripe = useStripe();
  const elements = useElements();

  const [message, setMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [clientSecret, setClientSecret] = useState("");

  useEffect(() => {
    // Create PaymentIntent as soon as the page loads
    fetch("/api/payment/create-payment-intent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        amount: amount * 100, // convert to cents
        metadata: { orderId }
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        setClientSecret(data.clientSecret);
      })
      .catch((error) => {
        setMessage("Failed to initialize payment. Please try again.");
        console.error("Error:", error);
      });
  }, [amount, orderId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) {
      // Stripe.js hasn't yet loaded.
      return;
    }

    setIsLoading(true);

    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/checkout/confirmation`,
      },
    });

    if (error) {
      setMessage(error.message ?? "An unexpected error occurred.");
    }

    setIsLoading(false);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Checkout</CardTitle>
        <CardDescription>Complete your purchase</CardDescription>
      </CardHeader>
      <CardContent>
        {clientSecret ? (
          <form id="payment-form" onSubmit={handleSubmit}>
            <PaymentElement id="payment-element" />
            {message && <div className="text-red-500 mt-2">{message}</div>}
            <Button 
              id="submit" 
              className="mt-4 w-full" 
              disabled={isLoading || !stripe || !elements} 
              type="submit"
            >
              {isLoading ? "Processing..." : "Pay Now"}
            </Button>
          </form>
        ) : (
          <div>Loading payment form...</div>
        )}
      </CardContent>
    </Card>
  );
}
```

### Create Checkout Page
```tsx
// app/checkout/page.tsx
"use client";

import { useSearchParams } from "next/navigation";
import StripeProvider from "@/components/payment/StripeProvider";
import CheckoutForm from "@/components/payment/CheckoutForm";
import { useEffect, useState } from "react";
import { Order } from "@/types";

export default function CheckoutPage() {
  const searchParams = useSearchParams();
  const orderId = searchParams.get("orderId");
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!orderId) {
      setError("Order ID is missing");
      setLoading(false);
      return;
    }

    // Fetch order details
    fetch(`/api/orders/${orderId}`)
      .then((res) => res.json())
      .then((data) => {
        setOrder(data);
        setLoading(false);
      })
      .catch((err) => {
        setError("Failed to load order details");
        setLoading(false);
        console.error(err);
      });
  }, [orderId]);

  if (loading) {
    return <div>Loading order details...</div>;
  }

  if (error || !order) {
    return <div>Error: {error || "Could not find order"}</div>;
  }

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-2xl font-bold mb-4">Complete Your Purchase</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <h2 className="text-xl font-semibold mb-4">Order Summary</h2>
          <div className="bg-gray-50 p-4 rounded-md">
            {order.items.map((item) => (
              <div key={item.id} className="flex justify-between mb-2">
                <span>{item.quantity}x {item.name}</span>
                <span>${item.price.toFixed(2)}</span>
              </div>
            ))}
            <div className="border-t border-gray-300 my-2 pt-2 font-semibold flex justify-between">
              <span>Total</span>
              <span>${order.total.toFixed(2)}</span>
            </div>
          </div>
        </div>
        
        <div>
          <h2 className="text-xl font-semibold mb-4">Payment Details</h2>
          <StripeProvider>
            <CheckoutForm amount={order.total} orderId={order.id} />
          </StripeProvider>
        </div>
      </div>
    </div>
  );
}
```

### Create Payment Confirmation Page
```tsx
// app/checkout/confirmation/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export default function ConfirmationPage() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"success" | "failure" | "processing" | "loading">("loading");
  const [orderId, setOrderId] = useState<string | null>(null);

  useEffect(() => {
    // Get the payment_intent and payment_intent_client_secret from URL
    const paymentIntent = searchParams.get("payment_intent");
    
    if (!paymentIntent) {
      setStatus("failure");
      return;
    }

    // Check payment status with your backend
    fetch(`/api/payment/status?paymentIntent=${paymentIntent}`)
      .then((res) => res.json())
      .then((data) => {
        setStatus(data.status);
        setOrderId(data.orderId);
      })
      .catch((err) => {
        console.error(err);
        setStatus("failure");
      });
  }, [searchParams]);

  if (status === "loading") {
    return <div>Verifying your payment...</div>;
  }

  return (
    <div className="container mx-auto py-8">
      <Card className="max-w-md mx-auto">
        <CardHeader>
          <CardTitle className="flex items-center">
            {status === "success" ? (
              <>
                <CheckCircle className="mr-2 h-6 w-6 text-green-500" />
                Payment Successful
              </>
            ) : (
              <>
                <XCircle className="mr-2 h-6 w-6 text-red-500" />
                Payment Failed
              </>
            )}
          </CardTitle>
          <CardDescription>
            {status === "success" 
              ? "Your payment was processed successfully."
              : "There was an issue processing your payment."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {status === "success" && orderId && (
            <div>
              <p>Order ID: {orderId}</p>
              <p>An email confirmation has been sent to your registered email address.</p>
            </div>
          )}
          {status === "failure" && (
            <p>Please try again or contact our support team for assistance.</p>
          )}
        </CardContent>
        <CardFooter className="flex flex-col sm:flex-row sm:justify-between gap-2">
          {status === "success" ? (
            <>
              <Button asChild variant="outline">
                <Link href="/orders">View Your Orders</Link>
              </Button>
              <Button asChild>
                <Link href="/events">Explore More Events</Link>
              </Button>
            </>
          ) : (
            <>
              <Button asChild variant="outline">
                <Link href="/checkout">Try Again</Link>
              </Button>
              <Button asChild>
                <Link href="/contact">Contact Support</Link>
              </Button>
            </>
          )}
        </CardFooter>
      </Card>
    </div>
  );
}
```

## 4. Testing Stripe Integration

### Test Cards
Use these card numbers for testing:

| Card Type | Number | Expiry | CVC | ZIP |
|-----------|--------|--------|-----|-----|
| Visa (Success) | 4242 4242 4242 4242 | Any future date | Any 3 digits | Any 5 digits |
| Visa (Decline) | 4000 0000 0000 0002 | Any future date | Any 3 digits | Any 5 digits |

### Testing Sequence
1. Create a test order
2. Proceed to checkout
3. Enter test card details
4. Confirm payment
5. Verify payment status
6. Check webhook handling

## 5. Security Considerations

1. **Secure API Keys**
   - Never expose your Stripe secret key in client-side code
   - Use environment variables for all sensitive information

2. **PCI Compliance**
   - Use Stripe Elements to avoid handling card data directly
   - Maintain proper security headers and content security policies

3. **Webhook Security**
   - Verify webhook signature using Stripe's utilities
   - Protect webhook endpoints from unauthorized access

4. **Error Handling**
   - Implement proper error handling at all steps
   - Avoid exposing sensitive information in error messages

5. **Idempotent Requests**
   - Use idempotency keys for critical operations
   - Handle duplicate webhook events properly

## 6. Going Live Checklist

1. Switch from test to live API keys
2. Update webhook endpoints in Stripe Dashboard
3. Update the return URL for payment confirmations
4. Verify that receipts and emails are properly configured
5. Test the entire payment flow in production environment
6. Set up Stripe Radar rules for fraud prevention

## Additional Resources

- [Stripe API Documentation](https://stripe.com/docs/api)
- [Stripe React Elements](https://stripe.com/docs/stripe-js/react)
- [Stripe Testing Guide](https://stripe.com/docs/testing)
- [Stripe Webhooks Guide](https://stripe.com/docs/webhooks)
- [Stripe Security Best Practices](https://stripe.com/docs/security) 