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
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PlusIcon, TrashIcon, PencilIcon } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { toast } from '@/hooks/use-toast';

import { TicketType, PriceTier } from '@/types';
import { getPriceTiers, deletePriceTier } from '@/lib/api/ticketService';
import { formatCurrency } from '@/lib/utils';
import PriceTierFormModal from './PriceTierFormModal';

interface PriceTiersTableProps {
  eventId: string;
  ticketTypes: TicketType[];
}

export default function PriceTiersTable({ eventId, ticketTypes }: PriceTiersTableProps) {
  const [selectedTicketTypeId, setSelectedTicketTypeId] = useState<string>('');
  const [priceTiers, setPriceTiers] = useState<PriceTier[]>([]);
  const [selectedPriceTier, setSelectedPriceTier] = useState<PriceTier | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Set default selected ticket type if available
    if (ticketTypes.length > 0 && !selectedTicketTypeId) {
      setSelectedTicketTypeId(ticketTypes[0].id);
    }
  }, [ticketTypes, selectedTicketTypeId]);

  useEffect(() => {
    // Fetch price tiers when ticket type changes
    if (selectedTicketTypeId) {
      fetchPriceTiers();
    }
  }, [selectedTicketTypeId]);

  const fetchPriceTiers = async () => {
    try {
      setIsLoading(true);
      const data = await getPriceTiers(selectedTicketTypeId);
      setPriceTiers(data);
    } catch (error) {
      console.error('Failed to fetch price tiers:', error);
      toast({
        title: 'Error',
        description: 'Failed to load price tiers',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreatePriceTier = () => {
    setSelectedPriceTier(null);
    setIsFormOpen(true);
  };

  const handleEditPriceTier = (priceTier: PriceTier) => {
    setSelectedPriceTier(priceTier);
    setIsFormOpen(true);
  };

  const handlePriceTierFormClose = (refreshData: boolean = false) => {
    setIsFormOpen(false);
    if (refreshData) {
      fetchPriceTiers();
    }
  };

  const handleDeletePriceTier = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this price tier?')) {
      try {
        await deletePriceTier(id);
        setPriceTiers(priceTiers.filter(pt => pt.id !== id));
        toast({
          title: 'Success',
          description: 'Price tier deleted successfully',
        });
      } catch (error) {
        console.error('Failed to delete price tier:', error);
        toast({
          title: 'Error',
          description: 'Failed to delete price tier',
          variant: 'destructive',
        });
      }
    }
  };

  // Determine the status of a price tier
  const getPriceTierStatus = (priceTier: PriceTier) => {
    if (!priceTier.isActive) {
      return <Badge variant="secondary">Inactive</Badge>;
    }
    
    const now = new Date();
    const startDate = new Date(priceTier.startDate);
    const endDate = new Date(priceTier.endDate);
    
    if (startDate > now) {
      return <Badge variant="outline">Upcoming</Badge>;
    }
    
    if (endDate < now) {
      return <Badge variant="outline">Ended</Badge>;
    }
    
    return <Badge variant="default">Active</Badge>;
  };

  const getTicketTypeName = (id: string) => {
    const ticketType = ticketTypes.find(tt => tt.id === id);
    return ticketType ? ticketType.name : 'Unknown';
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Select
            value={selectedTicketTypeId}
            onValueChange={setSelectedTicketTypeId}
          >
            <SelectTrigger className="w-[280px]">
              <SelectValue placeholder="Select a ticket type" />
            </SelectTrigger>
            <SelectContent>
              {ticketTypes.map((tt) => (
                <SelectItem key={tt.id} value={tt.id}>
                  {tt.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        <Button 
          onClick={handleCreatePriceTier}
          disabled={!selectedTicketTypeId}
        >
          <PlusIcon className="h-4 w-4 mr-2" /> Add Price Tier
        </Button>
      </div>
      
      {isLoading ? (
        <div className="flex justify-center p-4">
          <p>Loading price tiers...</p>
        </div>
      ) : (
        <Table>
          <TableCaption>Price tiers for {getTicketTypeName(selectedTicketTypeId)}</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Price</TableHead>
              <TableHead>Start Date</TableHead>
              <TableHead>End Date</TableHead>
              <TableHead>Quantity</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {!selectedTicketTypeId ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center">
                  Please select a ticket type
                </TableCell>
              </TableRow>
            ) : priceTiers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center">
                  No price tiers found
                </TableCell>
              </TableRow>
            ) : (
              priceTiers.map((priceTier) => (
                <TableRow key={priceTier.id}>
                  <TableCell className="font-medium">{priceTier.name}</TableCell>
                  <TableCell>{formatCurrency(priceTier.price, 'USD')}</TableCell>
                  <TableCell>
                    {new Date(priceTier.startDate).toLocaleDateString()} 
                    {' '}
                    {new Date(priceTier.startDate).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </TableCell>
                  <TableCell>
                    {new Date(priceTier.endDate).toLocaleDateString()} 
                    {' '}
                    {new Date(priceTier.endDate).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </TableCell>
                  <TableCell>
                    {priceTier.quantityAvailable ? priceTier.quantityAvailable : 'Unlimited'}
                  </TableCell>
                  <TableCell>{getPriceTierStatus(priceTier)}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="outline"
                      size="icon"
                      className="mr-2"
                      onClick={() => handleEditPriceTier(priceTier)}
                    >
                      <PencilIcon className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      className="text-destructive"
                      onClick={() => handleDeletePriceTier(priceTier.id)}
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
        <PriceTierFormModal
          ticketTypeId={selectedTicketTypeId}
          priceTier={selectedPriceTier}
          onClose={handlePriceTierFormClose}
        />
      )}
    </div>
  );
} 