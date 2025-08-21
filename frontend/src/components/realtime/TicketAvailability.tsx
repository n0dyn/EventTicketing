/**
 * Real-time Ticket Availability Component
 * Shows live ticket availability updates using WebSocket
 */

import React, { useEffect, useState } from 'react';
import { useTicketAvailability } from '../../hooks/useWebSocket';
import { Badge } from '../ui/badge';

interface TicketType {
  id: number;
  name: string;
  price: number;
  quantity: number;
  available_quantity: number;
}

interface TicketAvailabilityProps {
  eventId: number;
  tickets: TicketType[];
  onTicketUpdate?: (ticketId: number, availableQuantity: number) => void;
  className?: string;
}

export function TicketAvailability({ 
  eventId, 
  tickets, 
  onTicketUpdate,
  className = '' 
}: TicketAvailabilityProps) {
  const { ticketUpdates, availability, getAvailability, isConnected } = useTicketAvailability(eventId);
  const [animatingTickets, setAnimatingTickets] = useState<Set<number>>(new Set());

  useEffect(() => {
    // Notify parent component of ticket updates
    if (onTicketUpdate && ticketUpdates.length > 0) {
      const latestUpdate = ticketUpdates[0];
      onTicketUpdate(latestUpdate.ticket_type_id, latestUpdate.remaining_quantity);
    }
  }, [ticketUpdates, onTicketUpdate]);

  const getTicketAvailability = (ticket: TicketType): number => {
    const realtimeAvailability = getAvailability(ticket.id);
    return realtimeAvailability !== undefined ? realtimeAvailability : ticket.available_quantity;
  };

  const getAvailabilityStatus = (available: number, total: number) => {
    const percentage = (available / total) * 100;
    if (available === 0) return { status: 'sold-out', color: 'bg-red-500', text: 'Sold Out' };
    if (percentage <= 10) return { status: 'low', color: 'bg-orange-500', text: 'Low Stock' };
    if (percentage <= 25) return { status: 'medium', color: 'bg-yellow-500', text: 'Limited' };
    return { status: 'available', color: 'bg-green-500', text: 'Available' };
  };

  const handleTicketSoldAnimation = (ticketId: number) => {
    setAnimatingTickets(prev => new Set(prev).add(ticketId));
    setTimeout(() => {
      setAnimatingTickets(prev => {
        const newSet = new Set(prev);
        newSet.delete(ticketId);
        return newSet;
      });
    }, 2000);
  };

  // Animate when tickets are sold
  useEffect(() => {
    if (ticketUpdates.length > 0) {
      const latestUpdate = ticketUpdates[0];
      handleTicketSoldAnimation(latestUpdate.ticket_type_id);
    }
  }, [ticketUpdates]);

  return (
    <div className={`bg-white rounded-lg border shadow-sm ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-900">Ticket Availability</h3>
        <div className="flex items-center">
          <div 
            className={`w-2 h-2 rounded-full mr-2 ${
              isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
            }`}
          />
          <span className="text-xs text-gray-500">
            {isConnected ? 'Live Updates' : 'Offline'}
          </span>
        </div>
      </div>

      {/* Ticket List */}
      <div className="divide-y">
        {tickets.map((ticket) => {
          const available = getTicketAvailability(ticket);
          const statusInfo = getAvailabilityStatus(available, ticket.quantity);
          const isAnimating = animatingTickets.has(ticket.id);

          return (
            <div 
              key={ticket.id} 
              className={`p-4 transition-all duration-500 ${
                isAnimating ? 'bg-blue-50 scale-[1.02]' : 'hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h4 className="font-medium text-gray-900">{ticket.name}</h4>
                    <Badge 
                      variant={statusInfo.status === 'sold-out' ? 'destructive' : 
                               statusInfo.status === 'low' ? 'warning' : 'default'}
                      className="text-xs"
                    >
                      {statusInfo.text}
                    </Badge>
                  </div>
                  
                  <div className="flex items-center gap-4 mt-2">
                    <span className="text-lg font-bold text-gray-900">
                      ${ticket.price.toFixed(2)}
                    </span>
                    
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-600">
                        {available} / {ticket.quantity} available
                      </span>
                      
                      {/* Progress Bar */}
                      <div className="w-20 bg-gray-200 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full transition-all duration-500 ${statusInfo.color}`}
                          style={{ width: `${(available / ticket.quantity) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Animation indicator */}
                {isAnimating && (
                  <div className="flex items-center ml-4">
                    <div className="animate-bounce">
                      <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.293l-3-3a1 1 0 00-1.414 0l-3 3a1 1 0 001.414 1.414L9 9.414V13a1 1 0 102 0V9.414l1.293 1.293a1 1 0 001.414-1.414z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <span className="ml-1 text-xs text-blue-600 font-medium">
                      Just sold!
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Sales Activity */}
      {ticketUpdates.length > 0 && (
        <div className="border-t bg-gray-50 p-3">
          <h4 className="text-xs font-medium text-gray-700 mb-2">Recent Sales</h4>
          <div className="space-y-1">
            {ticketUpdates.slice(0, 3).map((update, index) => (
              <div key={index} className="flex items-center justify-between text-xs">
                <span className="text-gray-600">
                  {tickets.find(t => t.id === update.ticket_type_id)?.name}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">
                    -{update.quantity_sold} sold
                  </span>
                  <span className="text-gray-400">
                    {new Date(update.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default TicketAvailability;