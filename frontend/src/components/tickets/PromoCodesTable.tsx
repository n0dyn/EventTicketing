'use client';

import { useState, useEffect } from 'react';
import { 
  Table, 
  TableBody, 
  TableCaption, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PlusIcon, TrashIcon, PencilIcon, CheckIcon, XIcon } from 'lucide-react';
import { toast } from '@/hooks/use-toast';
import { Checkbox } from '@/components/ui/checkbox';

import { TicketType, PromoCode, DiscountType } from '@/types';
import { getPromoCodes, deletePromoCode } from '@/lib/api/ticketService';
import { formatCurrency } from '@/lib/utils';
import PromoCodeFormModal from './PromoCodeFormModal';

interface PromoCodesTableProps {
  eventId: string;
  ticketTypes: TicketType[];
}

export default function PromoCodesTable({ eventId, ticketTypes }: PromoCodesTableProps) {
  const [promoCodes, setPromoCodes] = useState<PromoCode[]>([]);
  const [selectedPromoCode, setSelectedPromoCode] = useState<PromoCode | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchPromoCodes();
  }, [eventId]);

  const fetchPromoCodes = async () => {
    try {
      setIsLoading(true);
      const data = await getPromoCodes(eventId);
      setPromoCodes(data);
    } catch (error) {
      console.error('Failed to fetch promo codes:', error);
      toast({
        title: 'Error',
        description: 'Failed to load promotional codes',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreatePromoCode = () => {
    setSelectedPromoCode(null);
    setIsFormOpen(true);
  };

  const handleEditPromoCode = (promoCode: PromoCode) => {
    setSelectedPromoCode(promoCode);
    setIsFormOpen(true);
  };

  const handlePromoCodeFormClose = (refreshData: boolean = false) => {
    setIsFormOpen(false);
    if (refreshData) {
      fetchPromoCodes();
    }
  };

  const handleDeletePromoCode = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this promotional code?')) {
      try {
        await deletePromoCode(id);
        setPromoCodes(promoCodes.filter(pc => pc.id !== id));
        toast({
          title: 'Success',
          description: 'Promotional code deleted successfully',
        });
      } catch (error) {
        console.error('Failed to delete promotional code:', error);
        toast({
          title: 'Error',
          description: 'Failed to delete promotional code',
          variant: 'destructive',
        });
      }
    }
  };

  // Format discount amount based on type
  const formatDiscount = (promoCode: PromoCode) => {
    if (promoCode.discountType === DiscountType.FIXED) {
      return formatCurrency(promoCode.discountAmount, 'USD');
    } else {
      return `${promoCode.discountAmount}%`;
    }
  };

  // Determine the status of a promo code
  const getPromoCodeStatus = (promoCode: PromoCode) => {
    if (!promoCode.isActive) {
      return <Badge variant="secondary">Inactive</Badge>;
    }
    
    const now = new Date();
    const startDate = promoCode.startDate ? new Date(promoCode.startDate) : null;
    const endDate = promoCode.endDate ? new Date(promoCode.endDate) : null;
    
    if (startDate && startDate > now) {
      return <Badge variant="outline">Upcoming</Badge>;
    }
    
    if (endDate && endDate < now) {
      return <Badge variant="outline">Expired</Badge>;
    }
    
    if (promoCode.usageLimit && promoCode.usageCount >= promoCode.usageLimit) {
      return <Badge variant="destructive">Limit Reached</Badge>;
    }
    
    return <Badge variant="default">Active</Badge>;
  };

  // Get applicable ticket types for a promo code
  const getApplicableTickets = (promoCode: PromoCode) => {
    if (!promoCode.ticketTypes || promoCode.ticketTypes.length === 0) {
      return 'All tickets';
    }
    
    return promoCode.ticketTypes
      .map(tt => tt.name)
      .join(', ');
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={handleCreatePromoCode}>
          <PlusIcon className="h-4 w-4 mr-2" /> Add Promo Code
        </Button>
      </div>
      
      {isLoading ? (
        <div className="flex justify-center p-4">
          <p>Loading promotional codes...</p>
        </div>
      ) : (
        <Table>
          <TableCaption>Promotional codes for this event</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>Code</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Discount</TableHead>
              <TableHead>Valid Period</TableHead>
              <TableHead>Usage</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Applies To</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {promoCodes.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center">
                  No promotional codes found
                </TableCell>
              </TableRow>
            ) : (
              promoCodes.map((promoCode) => (
                <TableRow key={promoCode.id}>
                  <TableCell className="font-medium uppercase">{promoCode.code}</TableCell>
                  <TableCell>{promoCode.description || '-'}</TableCell>
                  <TableCell>{formatDiscount(promoCode)}</TableCell>
                  <TableCell>
                    {promoCode.startDate && promoCode.endDate ? (
                      <>
                        {new Date(promoCode.startDate).toLocaleDateString()} - {' '}
                        {new Date(promoCode.endDate).toLocaleDateString()}
                      </>
                    ) : (
                      'No time limit'
                    )}
                  </TableCell>
                  <TableCell>
                    {promoCode.usageCount}
                    {promoCode.usageLimit ? ` / ${promoCode.usageLimit}` : ''}
                  </TableCell>
                  <TableCell>{getPromoCodeStatus(promoCode)}</TableCell>
                  <TableCell>{getApplicableTickets(promoCode)}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="outline"
                      size="icon"
                      className="mr-2"
                      onClick={() => handleEditPromoCode(promoCode)}
                    >
                      <PencilIcon className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      className="text-destructive"
                      onClick={() => handleDeletePromoCode(promoCode.id)}
                    >
                      <TrashIcon className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      )}
      
      {isFormOpen && (
        <PromoCodeFormModal
          eventId={eventId}
          ticketTypes={ticketTypes}
          promoCode={selectedPromoCode}
          onClose={handlePromoCodeFormClose}
        />
      )}
    </div>
  );
} 