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
import { toast } from '@/hooks/use-toast';
import { Label } from '@/components/ui/label';

import { TicketType, TicketTypeCreate, TicketTypeUpdate } from '@/types';
import { createTicketType, updateTicketType } from '@/lib/api/ticketService';

// Form validation schema - aligned with TicketTypeCreate interface
const formSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  description: z.string().optional(),
  price: z.number().min(0, 'Price must be 0 or higher'),
  quantityAvailable: z.number().int().min(0, 'Quantity must be 0 or higher'),
  isActive: z.boolean().default(true),
  saleStartDate: z.string().optional(),
  saleEndDate: z.string().optional(),
  minPerOrder: z.number().int().min(1, 'Minimum per order must be at least 1').default(1),
  maxPerOrder: z.number().int().min(0, 'Maximum per order must be 0 or higher').optional(),
  visibility: z.boolean().default(true),
  sortOrder: z.number().int().default(0)
});

type FormData = z.infer<typeof formSchema>;

interface TicketTypeFormProps {
  eventId: string;
  ticketType: TicketType | null;
  onClose: (refreshData?: boolean) => void;
}

export default function TicketTypeFormModal({ eventId, ticketType, onClose }: TicketTypeFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isEditing = !!ticketType;
  
  // Default form values
  const defaultValues: Partial<FormData> = ticketType ? {
    name: ticketType.name,
    description: ticketType.description || '',
    price: Number(ticketType.price),
    quantityAvailable: Number(ticketType.quantityAvailable),
    isActive: ticketType.isActive,
    saleStartDate: ticketType.saleStartDate || undefined,
    saleEndDate: ticketType.saleEndDate || undefined,
    minPerOrder: Number(ticketType.minPerOrder),
    maxPerOrder: ticketType.maxPerOrder ? Number(ticketType.maxPerOrder) : undefined,
    visibility: ticketType.visibility,
    sortOrder: Number(ticketType.sortOrder)
  } : {
    name: '',
    description: '',
    price: 0,
    quantityAvailable: 100,
    isActive: true,
    saleStartDate: undefined,
    saleEndDate: undefined,
    minPerOrder: 1,
    maxPerOrder: undefined,
    visibility: true,
    sortOrder: 0
  };
  
  // Form definition
  const form = useForm({
    defaultValues
  });
  
  // Form submission handler
  const onSubmit = async (values: any) => {
    setIsSubmitting(true);
    
    try {
      if (isEditing && ticketType) {
        // Update existing ticket type
        const updateData: TicketTypeUpdate = {
          name: values.name,
          description: values.description,
          price: values.price,
          quantityAvailable: values.quantityAvailable,
          isActive: values.isActive,
          saleStartDate: values.saleStartDate || undefined,
          saleEndDate: values.saleEndDate || undefined,
          minPerOrder: values.minPerOrder,
          maxPerOrder: values.maxPerOrder || undefined,
          visibility: values.visibility,
          sortOrder: values.sortOrder
        };
        
        await updateTicketType(ticketType.id, updateData);
        toast({
          title: 'Success',
          description: 'Ticket type updated successfully',
        });
      } else {
        // Create new ticket type
        const createData: TicketTypeCreate = {
          name: values.name,
          description: values.description,
          price: values.price,
          quantityAvailable: values.quantityAvailable,
          isActive: values.isActive,
          saleStartDate: values.saleStartDate || undefined,
          saleEndDate: values.saleEndDate || undefined,
          minPerOrder: values.minPerOrder,
          maxPerOrder: values.maxPerOrder || undefined,
          visibility: values.visibility,
          sortOrder: values.sortOrder
        };
        
        await createTicketType(eventId, createData);
        toast({
          title: 'Success',
          description: 'Ticket type created successfully',
        });
      }
      
      // Close the form and refresh the data
      onClose(true);
    } catch (error) {
      console.error('Failed to save ticket type:', error);
      toast({
        title: 'Error',
        description: `Failed to ${isEditing ? 'update' : 'create'} ticket type`,
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <Dialog open onOpenChange={() => onClose()}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit' : 'Create'} Ticket Type</DialogTitle>
          <DialogDescription>
            {isEditing 
              ? 'Update the details of this ticket type' 
              : 'Add a new ticket type to this event'}
          </DialogDescription>
        </DialogHeader>
        
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Name</FormLabel>
                      <FormControl>
                        <Input placeholder="General Admission, VIP, etc." {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              
              <div className="col-span-2">
                <FormField
                  control={form.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Description</FormLabel>
                      <FormControl>
                        <Textarea 
                          placeholder="Describe what's included with this ticket"
                          {...field}
                          value={field.value || ''}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              
              <div className="col-span-1">
                <FormField
                  control={form.control}
                  name="price"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Price</FormLabel>
                      <FormControl>
                        <Input 
                          type="number" 
                          min="0" 
                          step="0.01"
                          {...field}
                          onChange={(e) => field.onChange(parseFloat(e.target.value))}
                        />
                      </FormControl>
                      <FormDescription>
                        Set to 0 for free tickets
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              
              <div className="col-span-1">
                <FormField
                  control={form.control}
                  name="quantityAvailable"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Available Quantity</FormLabel>
                      <FormControl>
                        <Input 
                          type="number"
                          min="0"
                          step="1"
                          {...field}
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              
              <div className="col-span-1">
                <FormField
                  control={form.control}
                  name="saleStartDate"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Sale Start Date</FormLabel>
                      <FormControl>
                        <Input 
                          type="datetime-local"
                          {...field}
                          value={field.value || ''}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              
              <div className="col-span-1">
                <FormField
                  control={form.control}
                  name="saleEndDate"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Sale End Date</FormLabel>
                      <FormControl>
                        <Input 
                          type="datetime-local"
                          {...field}
                          value={field.value || ''}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              
              <div className="col-span-1">
                <FormField
                  control={form.control}
                  name="minPerOrder"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Min Per Order</FormLabel>
                      <FormControl>
                        <Input 
                          type="number"
                          min="1"
                          step="1"
                          {...field}
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              
              <div className="col-span-1">
                <FormField
                  control={form.control}
                  name="maxPerOrder"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Max Per Order</FormLabel>
                      <FormControl>
                        <Input 
                          type="number"
                          min="0"
                          step="1"
                          {...field}
                          value={field.value === null ? '' : field.value}
                          onChange={(e) => 
                            field.onChange(e.target.value ? parseInt(e.target.value) : null)
                          }
                        />
                      </FormControl>
                      <FormDescription>
                        Leave empty for no limit
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              
              <div className="col-span-1">
                <FormField
                  control={form.control}
                  name="sortOrder"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Sort Order</FormLabel>
                      <FormControl>
                        <Input 
                          type="number"
                          min="0"
                          step="1"
                          {...field}
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              
              <div className="col-span-1">
                <FormField
                  control={form.control}
                  name="isActive"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3 shadow-sm">
                      <div className="space-y-0.5">
                        <FormLabel>Active</FormLabel>
                        <FormDescription>
                          Enable or disable this ticket type
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
              </div>
              
              <div className="col-span-1">
                <FormField
                  control={form.control}
                  name="visibility"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3 shadow-sm">
                      <div className="space-y-0.5">
                        <FormLabel>Visible</FormLabel>
                        <FormDescription>
                          Show this ticket type to customers
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
              </div>
            </div>
            
            <DialogFooter>
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => onClose()}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button 
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting 
                  ? 'Saving...' 
                  : isEditing ? 'Update Ticket Type' : 'Create Ticket Type'
                }
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
} 