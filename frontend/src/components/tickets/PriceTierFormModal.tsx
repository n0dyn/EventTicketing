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
import { Switch } from '@/components/ui/switch';
import { toast } from '@/hooks/use-toast';

import { PriceTier } from '@/types';
import { createPriceTier, updatePriceTier } from '@/lib/api/ticketService';

// Form validation schema
const formSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  price: z.number().min(0, 'Price must be 0 or higher'),
  startDate: z.string().min(1, 'Start date is required'),
  endDate: z.string().min(1, 'End date is required'),
  quantityAvailable: z.number().int().min(0, 'Quantity must be 0 or higher').optional(),
  isActive: z.boolean().default(true),
});

type FormData = z.infer<typeof formSchema>;

interface PriceTierFormProps {
  ticketTypeId: string;
  priceTier: PriceTier | null;
  onClose: (refreshData?: boolean) => void;
}

export default function PriceTierFormModal({ ticketTypeId, priceTier, onClose }: PriceTierFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isEditing = !!priceTier;
  
  // Default form values
  const defaultValues: Partial<FormData> = priceTier ? {
    name: priceTier.name,
    price: Number(priceTier.price),
    startDate: priceTier.startDate ? new Date(priceTier.startDate).toISOString().slice(0, 16) : '',
    endDate: priceTier.endDate ? new Date(priceTier.endDate).toISOString().slice(0, 16) : '',
    quantityAvailable: priceTier.quantityAvailable || undefined,
    isActive: priceTier.isActive,
  } : {
    name: '',
    price: 0,
    startDate: '',
    endDate: '',
    quantityAvailable: undefined,
    isActive: true,
  };
  
  // Form definition
  const form = useForm({
    defaultValues
  });
  
  // Form submission handler
  const onSubmit = async (values: any) => {
    setIsSubmitting(true);
    
    try {
      if (isEditing && priceTier) {
        // Update existing price tier
        await updatePriceTier(priceTier.id, values);
        toast({
          title: 'Success',
          description: 'Price tier updated successfully',
        });
      } else {
        // Create new price tier
        await createPriceTier(ticketTypeId, values);
        toast({
          title: 'Success',
          description: 'Price tier created successfully',
        });
      }
      
      onClose(true); // Refresh data
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to save price tier',
      });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <Dialog open onOpenChange={() => onClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit' : 'Create'} Price Tier</DialogTitle>
          <DialogDescription>
            {isEditing 
              ? 'Update the details of this price tier' 
              : 'Add a new price tier to this ticket type'}
          </DialogDescription>
        </DialogHeader>
        
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name *</FormLabel>
                  <FormControl>
                    <Input placeholder="Early Bird" {...field} />
                  </FormControl>
                  <FormDescription>
                    Name for this pricing tier
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="price"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Price *</FormLabel>
                    <FormControl>
                      <Input 
                        type="number" 
                        step="0.01"
                        {...field}
                        onChange={(e) => field.onChange(parseFloat(e.target.value) || 0)}
                      />
                    </FormControl>
                    <FormDescription>
                      Price in dollars
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="quantityAvailable"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Quantity Available</FormLabel>
                    <FormControl>
                      <Input 
                        type="number" 
                        placeholder="Unlimited"
                        {...field}
                        onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
                      />
                    </FormControl>
                    <FormDescription>
                      Leave empty for unlimited
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="startDate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Start Date *</FormLabel>
                    <FormControl>
                      <Input 
                        type="datetime-local"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      When this pricing becomes available
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
                    <FormLabel>End Date *</FormLabel>
                    <FormControl>
                      <Input 
                        type="datetime-local"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      When this pricing expires
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="isActive"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">Active</FormLabel>
                    <FormDescription>
                      Enable or disable this price tier
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