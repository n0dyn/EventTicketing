'use client';

import { useState, useEffect } from 'react';
import { loadStripe, Stripe } from '@stripe/stripe-js';
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements
} from '@stripe/react-stripe-js';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from '@/hooks/use-toast';
import { 
  PaymentIntentCreate, 
  PaymentFormData, 
  PaymentConfig
} from '@/types';
import { 
  createPaymentIntent, 
  confirmPayment, 
  getPaymentConfig,
  formatAmount,
  convertToStripeAmount 
} from '@/lib/api/paymentService';

// Stripe instance (singleton)
let stripePromise: Promise<Stripe | null> | null = null;

const getStripe = async (): Promise<Stripe | null> => {
  if (!stripePromise) {
    // Get Stripe publishable key from backend
    try {
      const config = await getPaymentConfig();
      stripePromise = loadStripe(config.stripePublishableKey);
    } catch (error) {
      console.error('Failed to load Stripe config:', error);
      return null;
    }
  }
  return stripePromise;
};

interface PaymentFormProps {
  orderId: string;
  amount: number; // Amount in dollars
  currency?: string;
  description?: string;
  onSuccess?: (paymentId: string) => void;
  onError?: (error: string) => void;
  onCancel?: () => void;
}

// Internal payment form component that uses Stripe hooks
function PaymentFormContent({ orderId, amount, currency = 'USD', description, onSuccess, onError, onCancel }: PaymentFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  const [isProcessing, setIsProcessing] = useState(false);
  const [clientSecret, setClientSecret] = useState<string>('');
  const [paymentId, setPaymentId] = useState<string>('');
  
  const [customerData, setCustomerData] = useState<PaymentFormData>({
    email: '',
    name: '',
    phone: ''
  });

  // Create payment intent on component mount
  useEffect(() => {
    const createIntent = async () => {
      try {
        const paymentIntent: PaymentIntentCreate = {
          orderId,
          amount: convertToStripeAmount(amount),
          currency,
          description,
          metadata: {
            orderId,
            source: 'frontend_payment_form'
          }
        };

        const response = await createPaymentIntent(paymentIntent);
        setClientSecret(response.clientSecret);
        setPaymentId(response.payment.id);
      } catch (error) {
        console.error('Failed to create payment intent:', error);
        onError?.('Failed to initialize payment. Please try again.');
      }
    };

    createIntent();
  }, [orderId, amount, currency, description, onError]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!stripe || !elements || !clientSecret) {
      return;
    }

    setIsProcessing(true);

    try {
      // Confirm payment with Stripe
      const { error, paymentIntent } = await stripe.confirmPayment({
        elements,
        confirmParams: {
          return_url: `${window.location.origin}/payment/success`,
          payment_method_data: {
            billing_details: {
              name: customerData.name,
              email: customerData.email,
              phone: customerData.phone,
            },
          },
        },
        redirect: 'if_required',
      });

      if (error) {
        console.error('Payment failed:', error);
        onError?.(error.message || 'Payment failed. Please try again.');
        toast({
          title: 'Payment Failed',
          description: error.message || 'Your payment could not be processed.',
          variant: 'destructive',
        });
      } else if (paymentIntent && paymentIntent.status === 'succeeded') {
        // Payment succeeded
        toast({
          title: 'Payment Successful',
          description: 'Your payment has been processed successfully.',
        });
        onSuccess?.(paymentId);
      }
    } catch (error) {
      console.error('Payment error:', error);
      onError?.('An unexpected error occurred during payment.');
      toast({
        title: 'Payment Error',
        description: 'An unexpected error occurred. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleInputChange = (field: keyof PaymentFormData, value: string) => {
    setCustomerData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle>Payment Details</CardTitle>
        <CardDescription>
          Complete your payment for {formatAmount(convertToStripeAmount(amount), currency)}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Customer Information */}
          <div className="space-y-4">
            <div>
              <Label htmlFor="email">Email Address</Label>
              <Input
                id="email"
                type="email"
                value={customerData.email}
                onChange={(e) => handleInputChange('email', e.target.value)}
                placeholder="your.email@example.com"
                required
              />
            </div>
            
            <div>
              <Label htmlFor="name">Full Name</Label>
              <Input
                id="name"
                type="text"
                value={customerData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                placeholder="John Doe"
                required
              />
            </div>
            
            <div>
              <Label htmlFor="phone">Phone Number (Optional)</Label>
              <Input
                id="phone"
                type="tel"
                value={customerData.phone || ''}
                onChange={(e) => handleInputChange('phone', e.target.value)}
                placeholder="(555) 123-4567"
              />
            </div>
          </div>

          {/* Stripe Payment Element */}
          {clientSecret && (
            <div className="border rounded-md p-4">
              <Label className="text-sm font-medium mb-2 block">Payment Method</Label>
              <PaymentElement 
                options={{
                  layout: 'tabs',
                }}
              />
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            {onCancel && (
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                disabled={isProcessing}
                className="flex-1"
              >
                Cancel
              </Button>
            )}
            <Button
              type="submit"
              disabled={!stripe || isProcessing || !clientSecret}
              className="flex-1"
            >
              {isProcessing ? 'Processing...' : `Pay ${formatAmount(convertToStripeAmount(amount), currency)}`}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

// Main PaymentForm component with Stripe Elements provider
export default function PaymentForm(props: PaymentFormProps) {
  const [stripe, setStripe] = useState<Stripe | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initStripe = async () => {
      const stripeInstance = await getStripe();
      setStripe(stripeInstance);
      setLoading(false);
    };

    initStripe();
  }, []);

  if (loading) {
    return (
      <Card className="w-full max-w-md mx-auto">
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            <span className="ml-2">Loading payment form...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!stripe) {
    return (
      <Card className="w-full max-w-md mx-auto">
        <CardContent className="p-6">
          <div className="text-center text-red-600">
            Failed to load payment system. Please refresh the page.
          </div>
        </CardContent>
      </Card>
    );
  }

  const options = {
    mode: 'payment' as const,
    amount: convertToStripeAmount(props.amount),
    currency: props.currency || 'usd',
    appearance: {
      theme: 'stripe' as const,
    },
  };

  return (
    <Elements stripe={stripe} options={options}>
      <PaymentFormContent {...props} />
    </Elements>
  );
} 