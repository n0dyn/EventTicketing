'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription,
  CardFooter
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  Table, 
  TableBody, 
  TableCaption, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { PlusIcon, TrashIcon, PencilIcon, TagIcon } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from '@/hooks/use-toast';

import { TicketType, Event } from '@/types';
import { getTicketTypes, deleteTicketType } from '@/lib/api/ticketService';
import { formatCurrency } from '@/lib/utils';
import TicketTypeFormModal from '@/components/tickets/TicketTypeFormModal';
import PriceTiersTable from '@/components/tickets/PriceTiersTable';
import PromoCodesTable from '@/components/tickets/PromoCodesTable';

export default function EventTicketsPage() {
  const params = useParams();
  const router = useRouter();
  const eventId = params.eventId as string;
  
  const [event, setEvent] = useState<Event | null>(null);
  const [ticketTypes, setTicketTypes] = useState<TicketType[]>([]);
  const [selectedTicketType, setSelectedTicketType] = useState<TicketType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('ticket-types');
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const ticketTypesData = await getTicketTypes(eventId);
        setTicketTypes(ticketTypesData);
        // Fetch event data here when API is available
      } catch (error) {
        console.error('Failed to fetch data:', error);
        toast({
          title: 'Error',
          description: 'Failed to load ticket data',
          variant: 'destructive',
        });
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchData();
  }, [eventId]);
  
  const handleCreateTicketType = () => {
    setSelectedTicketType(null);
    setIsFormOpen(true);
  };
  
  const handleEditTicketType = (ticketType: TicketType) => {
    setSelectedTicketType(ticketType);
    setIsFormOpen(true);
  };
  
  const handleTicketFormClose = (refreshData: boolean = false) => {
    setIsFormOpen(false);
    if (refreshData) {
      // Refetch data if form was submitted successfully
      getTicketTypes(eventId)
        .then(data => setTicketTypes(data))
        .catch(error => {
          console.error('Failed to refresh ticket types:', error);
          toast({
            title: 'Error',
            description: 'Failed to refresh ticket data',
            variant: 'destructive',
          });
        });
    }
  };
  
  const handleDeleteTicketType = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this ticket type?')) {
      try {
        await deleteTicketType(id);
        setTicketTypes(ticketTypes.filter(tt => tt.id !== id));
        toast({
          title: 'Success',
          description: 'Ticket type deleted successfully',
        });
      } catch (error) {
        console.error('Failed to delete ticket type:', error);
        toast({
          title: 'Error',
          description: 'Failed to delete ticket type',
          variant: 'destructive',
        });
      }
    }
  };
  
  const getAvailabilityDisplay = (ticketType: TicketType) => {
    const now = new Date();
    const startDate = ticketType.saleStartDate ? new Date(ticketType.saleStartDate) : null;
    const endDate = ticketType.saleEndDate ? new Date(ticketType.saleEndDate) : null;
    
    if (!ticketType.isActive) {
      return <Badge variant="secondary">Inactive</Badge>;
    }
    
    if (startDate && startDate > now) {
      return <Badge variant="outline">Upcoming</Badge>;
    }
    
    if (endDate && endDate < now) {
      return <Badge variant="outline">Ended</Badge>;
    }
    
    if (ticketType.quantityAvailable === 0) {
      return <Badge variant="destructive">Sold Out</Badge>;
    }
    
    return <Badge variant="default">On Sale</Badge>;
  };
  
  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">
          Ticket Management
        </h1>
        <Button onClick={() => router.back()}>Back to Event</Button>
      </div>
      
      <Tabs
        defaultValue="ticket-types"
        value={activeTab}
        onValueChange={setActiveTab}
        className="w-full"
      >
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="ticket-types">Ticket Types</TabsTrigger>
          <TabsTrigger value="price-tiers">Price Tiers</TabsTrigger>
          <TabsTrigger value="promo-codes">Promo Codes</TabsTrigger>
        </TabsList>
        
        <TabsContent value="ticket-types" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Ticket Types</CardTitle>
              <CardDescription>Manage ticket types for this event</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex justify-center p-4">
                  <p>Loading ticket types...</p>
                </div>
              ) : (
                <Table>
                  <TableCaption>List of available ticket types for this event</TableCaption>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Price</TableHead>
                      <TableHead>Quantity</TableHead>
                      <TableHead>Availability</TableHead>
                      <TableHead>Sale Period</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {ticketTypes.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center">
                          No ticket types found
                        </TableCell>
                      </TableRow>
                    ) : (
                      ticketTypes.map((ticketType) => (
                        <TableRow key={ticketType.id}>
                          <TableCell className="font-medium">{ticketType.name}</TableCell>
                          <TableCell>
                            {ticketType.price === 0
                              ? 'Free'
                              : formatCurrency(ticketType.price, 'USD')}
                          </TableCell>
                          <TableCell>{ticketType.quantityAvailable}</TableCell>
                          <TableCell>{getAvailabilityDisplay(ticketType)}</TableCell>
                          <TableCell>
                            {ticketType.saleStartDate && ticketType.saleEndDate ? (
                              <>
                                {new Date(ticketType.saleStartDate).toLocaleDateString()} - {' '}
                                {new Date(ticketType.saleEndDate).toLocaleDateString()}
                              </>
                            ) : (
                              'No restrictions'
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="outline"
                              size="icon"
                              className="mr-2"
                              onClick={() => handleEditTicketType(ticketType)}
                            >
                              <PencilIcon className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="outline"
                              size="icon"
                              className="text-destructive"
                              onClick={() => handleDeleteTicketType(ticketType.id)}
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
            </CardContent>
            <CardFooter>
              <Button 
                onClick={handleCreateTicketType}
                className="ml-auto"
              >
                <PlusIcon className="h-4 w-4 mr-2" /> Add Ticket Type
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>
        
        <TabsContent value="price-tiers" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Price Tiers</CardTitle>
              <CardDescription>Manage price tiers for your tickets</CardDescription>
            </CardHeader>
            <CardContent>
              <PriceTiersTable 
                eventId={eventId} 
                ticketTypes={ticketTypes} 
              />
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="promo-codes" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Promotional Codes</CardTitle>
              <CardDescription>Manage promotional codes for discounts</CardDescription>
            </CardHeader>
            <CardContent>
              <PromoCodesTable 
                eventId={eventId} 
                ticketTypes={ticketTypes}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      
      {isFormOpen && (
        <TicketTypeFormModal
          eventId={eventId}
          ticketType={selectedTicketType}
          onClose={handleTicketFormClose}
        />
      )}
    </div>
  );
} 