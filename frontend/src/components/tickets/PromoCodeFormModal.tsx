'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle 
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  Form, 
  FormControl, 
  FormDescription, 
  FormField, 
  FormItem, 
  FormLabel, 
  FormMessage 
} from '@/components/ui/form';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from '@/hooks/use-toast';

import { PromoCode, TicketType, DiscountType } from '@/types';
import { createPromoCode, updatePromoCode } from '@/lib/api/ticketService';

// Form validation schema
const formSchema = z.object({
  code: z.string().min(3, 'Code must be at least 3 characters').max(20, 'Code must be less than 20 characters'),
  description: z.string().optional(),
  discountType: z.nativeEnum(DiscountType),
  discountAmount: z.number().min(0, 'Discount amount must be positive'),
  startDate: z.string().optional(),
  endDate: z.string().optional(),
  usageLimit: z.number().int().min(1, 'Usage limit must be at least 1').optional(),
  isActive: z.boolean().default(true),
  ticketTypeIds: z.array(z.string()).min(1, 'Select at least one ticket type'),
});

type FormData = z.infer<typeof formSchema>;

interface PromoCodeFormProps {
  eventId: string;
  ticketTypes: TicketType[];
  promoCode: PromoCode | null;
  onClose: (refreshData?: boolean) => void;
}

export default function PromoCodeFormModal({ eventId, ticketTypes, promoCode, onClose }: PromoCodeFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isEditing = !!promoCode;
  
  // Default form values
  const defaultValues: Partial<FormData> = promoCode ? {
    code: promoCode.code,
    description: promoCode.description || '',
    discountType: promoCode.discountType,
    discountAmount: Number(promoCode.discountAmount),
    startDate: promoCode.startDate || undefined,
    endDate: promoCode.endDate || undefined,
    usageLimit: promoCode.usageLimit || undefined,
    isActive: promoCode.isActive,
    ticketTypeIds: promoCode.ticketTypes?.map(tt => tt.id) || [],
  } : {
    code: '',
    description: '',
    discountType: DiscountType.PERCENTAGE,
    discountAmount: 10,
    startDate: undefined,
    endDate: undefined,
    usageLimit: undefined,
    isActive: true,
    ticketTypeIds: [],
  };
  
  // Form definition
  const form = useForm({
    defaultValues
  });
  
  // Form submission handler
  const onSubmit = async (values: any) => {
    setIsSubmitting(true);
    
    try {
      if (isEditing && promoCode) {
        // Update existing promo code
        await updatePromoCode(promoCode.id, values);
        toast({
          title: 'Success',
          description: 'Promo code updated successfully',
        });
      } else {
        // Create new promo code
        await createPromoCode(eventId, values);
        toast({
          title: 'Success',
          description: 'Promo code created successfully',
        });
      }
      
      onClose(true); // Refresh data
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to save promo code',
      });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <Dialog open onOpenChange={() => onClose()}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit' : 'Create'} Promo Code</DialogTitle>
          <DialogDescription>
            {isEditing 
              ? 'Update the details of this promo code' 
              : 'Add a new promo code to this event'}
          </DialogDescription>
        </DialogHeader>
        
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Promo Code *</FormLabel>
                    <FormControl>
                      <Input placeholder="SAVE20" {...field} />
                    </FormControl>
                    <FormDescription>
                      Unique code customers will enter
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="discountType"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Discount Type *</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select discount type" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value={DiscountType.PERCENTAGE}>Percentage</SelectItem>
                        <SelectItem value={DiscountType.FIXED}>Fixed Amount</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="discountAmount"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Discount Amount *</FormLabel>
                    <FormControl>
                      <Input 
                        type="number" 
                        step="0.01"
                        {...field}
                        onChange={(e) => field.onChange(parseFloat(e.target.value) || 0)}
                      />
                    </FormControl>
                    <FormDescription>
                      {form.watch('discountType') === DiscountType.PERCENTAGE ? 'Percentage (0-100)' : 'Amount in dollars'}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="usageLimit"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Usage Limit</FormLabel>
                    <FormControl>
                      <Input 
                        type="number" 
                        placeholder="Unlimited"
                        {...field}
                        onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
                      />
                    </FormControl>
                    <FormDescription>
                      Maximum number of uses (leave empty for unlimited)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea 
                      placeholder="Optional description for internal use"
                      className="resize-none"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="startDate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Start Date</FormLabel>
                    <FormControl>
                      <Input 
                        type="datetime-local"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      When the promo code becomes active
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="endDate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>End Date</FormLabel>
                    <FormControl>
                      <Input 
                        type="datetime-local"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      When the promo code expires
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="ticketTypeIds"
              render={() => (
                <FormItem>
                  <div className="mb-4">
                    <FormLabel className="text-base">Applicable Ticket Types *</FormLabel>
                    <FormDescription>
                      Select which ticket types this promo code applies to
                    </FormDescription>
                  </div>
                  {ticketTypes.map((ticketType) => (
                    <FormField
                      key={ticketType.id}
                      control={form.control}
                      name="ticketTypeIds"
                      render={({ field }) => {
                        return (
                          <FormItem
                            key={ticketType.id}
                            className="flex flex-row items-start space-x-3 space-y-0"
                          >
                            <FormControl>
                              <Checkbox
                                checked={field.value?.includes(ticketType.id)}
                                onCheckedChange={(checked) => {
                                  return checked
                                    ? field.onChange([...(field.value || []), ticketType.id])
                                    : field.onChange(
                                        (field.value || []).filter(
                                          (value) => value !== ticketType.id
                                        )
                                      )
                                }}
                              />
                            </FormControl>
                            <FormLabel className="font-normal">
                              {ticketType.name} - ${ticketType.price}
                            </FormLabel>
                          </FormItem>
                        )
                      }}
                    />
                  ))}
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="isActive"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">Active</FormLabel>
                    <FormDescription>
                      Enable or disable this promo code
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                </FormItem>
              )}
            />
            
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onClose()}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : (isEditing ? 'Update' : 'Create')}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
} 