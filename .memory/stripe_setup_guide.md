# Stripe Setup Guide for EventTicketing

## Overview
This guide explains how to set up Stripe payment processing for the EventTicketing platform.

## Development Setup

### 1. Create Stripe Account
1. Visit [Stripe Dashboard](https://dashboard.stripe.com/)
2. Create a new account or log into existing account
3. Switch to "Test mode" in the dashboard

### 2. Get API Keys
1. Navigate to **Developers > API keys** in the Stripe dashboard
2. Copy the **Publishable key** (starts with `pk_test_`)
3. Copy the **Secret key** (starts with `sk_test_`)

### 3. Configure Environment Variables

#### Frontend (.env.local)
```env
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_actual_key_here
```

#### Backend (.env)
```env
STRIPE_SECRET_KEY=sk_test_your_actual_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_actual_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
STRIPE_CURRENCY=USD
```

### 4. Set Up Webhooks (Optional for Development)
1. In Stripe Dashboard, go to **Developers > Webhooks**
2. Click **Add endpoint**
3. Set endpoint URL: `http://localhost:8000/api/v1/payments/stripe/webhook`
4. Select events to listen for:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Copy the webhook signing secret

## Implementation Status

### ✅ Completed
- Payment database models (Payment, Refund, PaymentWebhook, PaymentAttempt)
- Payment service layer with Stripe integration
- Payment API endpoints
- Frontend payment service
- PaymentForm component with Stripe Elements
- TypeScript type definitions

### 🔄 In Progress
- Environment configuration setup

### ⏳ Pending
- End-to-end payment flow testing
- Receipt generation
- Refund processing UI

## Testing Payment Flow

### Test Card Numbers
Use these test card numbers for development:

**Successful Payments:**
- Visa: `4242424242424242`
- Mastercard: `5555555555554444`
- American Express: `378282246310005`

**Failed Payments:**
- Declined: `4000000000000002`
- Insufficient funds: `4000000000009995`
- Expired card: `4000000000000069`

### Security Notes
- Never commit real API keys to version control
- Use environment variables for all sensitive configuration
- Always use HTTPS in production
- Validate webhook signatures to ensure security

## Next Steps
1. Replace placeholder API keys with real test keys
2. Test payment flow with test cards
3. Implement receipt generation
4. Set up production webhook endpoints
5. Configure production environment variables