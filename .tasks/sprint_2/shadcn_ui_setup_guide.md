# Setting up shadcn/ui for Ticket Management System

## Overview
This guide provides step-by-step instructions for setting up shadcn/ui components needed to complete the ticket management system frontend implementation. shadcn/ui is a collection of reusable components built with Radix UI and Tailwind CSS.

## Prerequisites
- Node.js (v14.0.0 or later)
- npm or yarn
- Next.js project set up
- Tailwind CSS configured in the project

## Installation Steps

### 1. Initialize shadcn/ui in Your Project

Run the initialization command in your project root:

```bash
npx shadcn@latest init
```

During the initialization, you'll be prompted to select various options:

- **Which style would you like to use?** › `Default`
- **Which color would you like to use as base color?** › `Slate`
- **Where is your global CSS file?** › `app/globals.css` (adjust based on your project structure)
- **Do you want to use CSS variables for colors?** › `Yes`
- **Where is your tailwind.config.js located?** › `tailwind.config.js`
- **Configure the import alias for components?** › `@/components`
- **Configure the import alias for utils?** › `@/lib/utils`
- **Are you using React Server Components?** › `Yes` (for Next.js App Router)

### 2. Install Core Components for Ticket Management

```bash
# UI components for forms and inputs
npx shadcn@latest add button
npx shadcn@latest add form
npx shadcn@latest add input
npx shadcn@latest add label
npx shadcn@latest add select
npx shadcn@latest add checkbox
npx shadcn@latest add switch
npx shadcn@latest add textarea

# UI components for layout and organization
npx shadcn@latest add tabs
npx shadcn@latest add card
npx shadcn@latest add table
npx shadcn@latest add dialog
npx shadcn@latest add sheet
npx shadcn@latest add separator
npx shadcn@latest add scroll-area

# UI components for dates and feedback
npx shadcn@latest add calendar
npx shadcn@latest add date-picker
npx shadcn@latest add toast
npx shadcn@latest add tooltip
```

### 3. Set Up Component Utilities

Ensure you have the necessary utility functions in your project:

```typescript
// lib/utils.ts
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number, currency = 'USD') {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
  }).format(amount);
}

export function formatDate(date: Date | string) {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}
```

### 4. Create Custom Ticket Form Components

#### Ticket Type Form

```tsx
// components/ticket/ticket-type-form.tsx
"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "@/components/ui/use-toast"

const ticketTypeSchema = z.object({
  name: z.string().min(2, {
    message: "Name must be at least 2 characters.",
  }),
  description: z.string().optional(),
  price: z.coerce.number().min(0, {
    message: "Price must be a positive number.",
  }),
  quantity: z.coerce.number().int().min(1, {
    message: "Quantity must be at least 1.",
  }),
  startDate: z.date(),
  endDate: z.date(),
})

export function TicketTypeForm({ 
  ticketType, 
  onSubmit 
}: { 
  ticketType?: any, 
  onSubmit: (values: z.infer<typeof ticketTypeSchema>) => void 
}) {
  const form = useForm<z.infer<typeof ticketTypeSchema>>({
    resolver: zodResolver(ticketTypeSchema),
    defaultValues: ticketType || {
      name: "",
      description: "",
      price: 0,
      quantity: 1,
      startDate: new Date(),
      endDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days from now
    },
  })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input placeholder="General Admission" {...field} />
              </FormControl>
              <FormDescription>
                The name of the ticket type.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea placeholder="Describe the ticket benefits..." {...field} />
              </FormControl>
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
                <FormLabel>Price</FormLabel>
                <FormControl>
                  <Input type="number" min="0" step="0.01" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          
          <FormField
            control={form.control}
            name="quantity"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Quantity</FormLabel>
                <FormControl>
                  <Input type="number" min="1" step="1" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          {/* Date picker fields would go here */}
        </div>
        
        <Button type="submit">Save Ticket Type</Button>
      </form>
    </Form>
  )
}
```

### 5. Set Up Data Table for Ticket Types

```tsx
// components/ticket/ticket-type-table.tsx
"use client"

import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { formatCurrency, formatDate } from "@/lib/utils"
import { Edit, Trash } from "lucide-react"

type TicketType = {
  id: string
  name: string
  description?: string
  price: number
  quantity: number
  startDate: string
  endDate: string
  status: 'active' | 'inactive' | 'sold_out'
}

export function TicketTypeTable({
  ticketTypes,
  onEdit,
  onDelete
}: {
  ticketTypes: TicketType[]
  onEdit: (id: string) => void
  onDelete: (id: string) => void
}) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Price</TableHead>
            <TableHead>Quantity</TableHead>
            <TableHead>Sales Period</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {ticketTypes.map((ticket) => (
            <TableRow key={ticket.id}>
              <TableCell className="font-medium">{ticket.name}</TableCell>
              <TableCell>{formatCurrency(ticket.price)}</TableCell>
              <TableCell>{ticket.quantity}</TableCell>
              <TableCell>
                {formatDate(ticket.startDate)} - {formatDate(ticket.endDate)}
              </TableCell>
              <TableCell>
                <span className={`px-2 py-1 rounded-full text-xs ${
                  ticket.status === 'active' 
                    ? 'bg-green-100 text-green-800' 
                    : ticket.status === 'inactive'
                    ? 'bg-gray-100 text-gray-800'
                    : 'bg-red-100 text-red-800'
                }`}>
                  {ticket.status.replace('_', ' ')}
                </span>
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-2">
                  <Button 
                    variant="outline" 
                    size="icon" 
                    onClick={() => onEdit(ticket.id)}
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button 
                    variant="outline" 
                    size="icon" 
                    onClick={() => onDelete(ticket.id)}
                  >
                    <Trash className="h-4 w-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
```

### 6. Create Main Ticket Management Page

```tsx
// app/dashboard/tickets/page.tsx
"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TicketTypeTable } from "@/components/ticket/ticket-type-table"
import { PriceTierTable } from "@/components/ticket/price-tier-table"
import { PromoCodeTable } from "@/components/ticket/promo-code-table"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { TicketTypeForm } from "@/components/ticket/ticket-type-form"
import { Plus } from "lucide-react"

// Mock data for demonstration
const ticketTypes = [
  {
    id: "1",
    name: "General Admission",
    price: 25,
    quantity: 200,
    startDate: "2025-06-01",
    endDate: "2025-07-01",
    status: "active" as const
  },
  // Add more mock data as needed
]

export default function TicketsPage() {
  const [activeTab, setActiveTab] = useState("ticket-types")
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingTicket, setEditingTicket] = useState<any>(null)

  const handleCreateTicket = () => {
    setEditingTicket(null)
    setIsDialogOpen(true)
  }

  const handleEditTicket = (id: string) => {
    // In a real app, you would fetch the ticket details
    const ticket = ticketTypes.find((t) => t.id === id)
    setEditingTicket(ticket)
    setIsDialogOpen(true)
  }

  const handleDeleteTicket = (id: string) => {
    // In a real app, you would call an API to delete the ticket
    console.log("Delete ticket", id)
  }

  const handleSubmitTicket = (values: any) => {
    // In a real app, you would call an API to create/update the ticket
    console.log("Submit ticket", values)
    setIsDialogOpen(false)
  }

  return (
    <div className="container mx-auto py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Ticket Management</h1>
        <Button onClick={handleCreateTicket}>
          <Plus className="mr-2 h-4 w-4" /> Add Ticket Type
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="ticket-types">Ticket Types</TabsTrigger>
          <TabsTrigger value="price-tiers">Price Tiers</TabsTrigger>
          <TabsTrigger value="promo-codes">Promo Codes</TabsTrigger>
        </TabsList>
        <TabsContent value="ticket-types" className="mt-6">
          <TicketTypeTable 
            ticketTypes={ticketTypes}
            onEdit={handleEditTicket}
            onDelete={handleDeleteTicket}
          />
        </TabsContent>
        <TabsContent value="price-tiers" className="mt-6">
          {/* Price tier table content */}
        </TabsContent>
        <TabsContent value="promo-codes" className="mt-6">
          {/* Promo code table content */}
        </TabsContent>
      </Tabs>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>
              {editingTicket ? "Edit Ticket Type" : "Create Ticket Type"}
            </DialogTitle>
          </DialogHeader>
          <TicketTypeForm 
            ticketType={editingTicket} 
            onSubmit={handleSubmitTicket} 
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}
```

## Troubleshooting

### Common Issues and Solutions

1. **Component not found errors**
   - Ensure you've run the appropriate add command for each component
   - Check import paths match your project's configuration

2. **Styling issues**
   - Verify your Tailwind CSS configuration includes all necessary plugins
   - Check that your global CSS imports the Tailwind directives

3. **TypeScript errors**
   - Install any missing type definitions with `npm install -D @types/package-name`
   - Update your TypeScript configuration if needed

## Additional Resources

- [shadcn/ui Documentation](https://ui.shadcn.com/)
- [Radix UI Documentation](https://www.radix-ui.com/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Next.js Documentation](https://nextjs.org/docs)

## Next Steps

After completing the shadcn/ui setup:

1. Connect your UI components to the backend API endpoints
2. Implement form validation and error handling
3. Test the complete ticket management workflow
4. Style components according to your project's design guidelines 