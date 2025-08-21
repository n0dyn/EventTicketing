'use client';

import { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  CheckCircle, 
  Download, 
  Mail, 
  CreditCard,
  Calendar,
  MapPin,
  Ticket
} from 'lucide-react';
import { toast } from '@/hooks/use-toast';

import { PaymentConfirmResponse } from '@/types/payment';

interface PaymentReceiptProps {
  paymentData: PaymentConfirmResponse;
  onClose?: () => void;
}

export default function PaymentReceipt({ paymentData, onClose }: PaymentReceiptProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [isSendingEmail, setIsSendingEmail] = useState(false);

  const handleDownloadReceipt = async () => {
    setIsDownloading(true);
    try {
      // In a real implementation, this would call an API to generate PDF
      // For now, we'll just show a toast
      toast({
        title: 'Receipt Download',
        description: 'Receipt download will be available when backend is connected',
      });
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: 'Failed to download receipt',
      });
    } finally {
      setIsDownloading(false);
    }
  };

  const handleEmailReceipt = async () => {
    setIsSendingEmail(true);
    try {
      // In a real implementation, this would call an API to send email
      toast({
        title: 'Email Sent',
        description: 'Receipt email will be available when backend is connected',
      });
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: 'Failed to send receipt email',
      });
    } finally {
      setIsSendingEmail(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <Card>
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <CheckCircle className="h-16 w-16 text-green-500" />
          </div>
          <CardTitle className="text-2xl text-green-600">Payment Successful!</CardTitle>
          <CardDescription>
            Your payment has been processed successfully. You will receive a confirmation email shortly.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Payment Details */}
          <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="text-sm font-medium text-gray-500">Payment ID</p>
              <p className="text-sm">{paymentData.paymentIntentId}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Amount Paid</p>
              <p className="text-lg font-semibold">
                ${(paymentData.amountReceived / 100).toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Payment Method</p>
              <div className="flex items-center space-x-2">
                <CreditCard className="h-4 w-4" />
                <span className="text-sm">{paymentData.paymentMethod}</span>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Status</p>
              <Badge variant="default" className="bg-green-100 text-green-800">
                {paymentData.status}
              </Badge>
            </div>
          </div>

          {/* Order Summary */}
          {paymentData.order && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Order Summary</h3>
              <div className="border rounded-lg p-4">
                <div className="flex items-start space-x-4">
                  <Ticket className="h-6 w-6 text-blue-500 mt-1" />
                  <div className="flex-1">
                    <h4 className="font-medium">{paymentData.order.eventTitle}</h4>
                    <div className="flex items-center space-x-4 text-sm text-gray-500 mt-1">
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>
                          {paymentData.order.eventDate 
                            ? format(new Date(paymentData.order.eventDate), 'PPP p')
                            : 'Date TBD'}
                        </span>
                      </div>
                      {paymentData.order.eventLocation && (
                        <div className="flex items-center space-x-1">
                          <MapPin className="h-4 w-4" />
                          <span>{paymentData.order.eventLocation}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Tickets */}
                {paymentData.order.tickets && paymentData.order.tickets.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <h5 className="font-medium text-sm">Tickets:</h5>
                    {paymentData.order.tickets.map((ticket: any, index: number) => (
                      <div key={index} className="flex justify-between items-center py-2 px-3 bg-gray-50 rounded">
                        <span className="text-sm">{ticket.ticketTypeName}</span>
                        <div className="flex items-center space-x-4">
                          <span className="text-sm">Qty: {ticket.quantity}</span>
                          <span className="text-sm font-medium">
                            ${(ticket.price * ticket.quantity).toFixed(2)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Next Steps */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">What's Next?</h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-start space-x-2">
                <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
                <span>You will receive a confirmation email with your ticket details</span>
              </div>
              <div className="flex items-start space-x-2">
                <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
                <span>Your tickets will be available in your account dashboard</span>
              </div>
              <div className="flex items-start space-x-2">
                <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
                <span>Bring a valid photo ID to the event for entry</span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3 pt-4">
            <Button 
              onClick={handleDownloadReceipt}
              disabled={isDownloading}
              className="flex-1"
            >
              <Download className="h-4 w-4 mr-2" />
              {isDownloading ? 'Downloading...' : 'Download Receipt'}
            </Button>
            
            <Button 
              variant="outline"
              onClick={handleEmailReceipt}
              disabled={isSendingEmail}
              className="flex-1"
            >
              <Mail className="h-4 w-4 mr-2" />
              {isSendingEmail ? 'Sending...' : 'Email Receipt'}
            </Button>

            {onClose && (
              <Button variant="secondary" onClick={onClose}>
                Continue
              </Button>
            )}
          </div>

          {/* Support */}
          <div className="pt-4 text-center text-sm text-gray-500">
            <p>Need help? Contact our support team at support@eventticketing.com</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}