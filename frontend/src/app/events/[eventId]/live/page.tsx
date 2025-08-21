/**
 * Live Event Dashboard Page
 * Demonstrates real-time WebSocket features for event management
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '../../../../hooks/useAuth';
import LiveEventStats from '../../../../components/realtime/LiveEventStats';
import TicketAvailability from '../../../../components/realtime/TicketAvailability';
import AdminNotifications from '../../../../components/realtime/AdminNotifications';
import { Card, CardContent, CardHeader, CardTitle } from '../../../../components/ui/card';
import { Badge } from '../../../../components/ui/badge';
import { Button } from '../../../../components/ui/button';
import { useEventWebSocket } from '../../../../hooks/useWebSocket';

// Mock data - in real app, this would come from API
const mockEvent = {
  id: 1,
  title: 'Tech Conference 2024',
  description: 'Annual technology conference',
  startDate: new Date('2024-09-15T09:00:00Z'),
  endDate: new Date('2024-09-15T18:00:00Z'),
  location: 'Convention Center',
  status: 'active'
};

const mockTickets = [
  {
    id: 1,
    name: 'Early Bird',
    price: 89.99,
    quantity: 100,
    available_quantity: 25
  },
  {
    id: 2,
    name: 'Regular',
    price: 129.99,
    quantity: 200,
    available_quantity: 78
  },
  {
    id: 3,
    name: 'VIP',
    price: 299.99,
    quantity: 50,
    available_quantity: 12
  }
];

export default function LiveEventPage() {
  const params = useParams();
  const eventId = parseInt(params?.eventId as string) || 1;
  const { user, token } = useAuth();
  
  // WebSocket connection for general event updates
  const { 
    isConnected: eventConnected, 
    lastMessage: eventMessage, 
    onMessage: onEventMessage 
  } = useEventWebSocket(eventId);

  const [recentEvents, setRecentEvents] = useState<any[]>([]);
  const [eventStats, setEventStats] = useState({
    totalTicketsSold: 0,
    totalRevenue: 0,
    conversionRate: 0
  });

  // Handle real-time event messages
  useEffect(() => {
    if (!onEventMessage) return;

    const unsubscribes = [
      onEventMessage('ticket_sold', (message) => {
        const data = message.data;
        setRecentEvents(prev => [
          {
            type: 'ticket_sold',
            message: `${data.quantity_sold} ${data.ticket_name} ticket(s) sold`,
            timestamp: new Date().toISOString(),
            data
          },
          ...prev.slice(0, 9)
        ]);

        // Update stats
        setEventStats(prev => ({
          ...prev,
          totalTicketsSold: prev.totalTicketsSold + data.quantity_sold,
          totalRevenue: prev.totalRevenue + (data.quantity_sold * data.price || 0)
        }));
      }),

      onEventMessage('event_updated', (message) => {
        setRecentEvents(prev => [
          {
            type: 'event_updated',
            message: 'Event details updated',
            timestamp: new Date().toISOString(),
            data: message.data
          },
          ...prev.slice(0, 9)
        ]);
      }),

      onEventMessage('attendee_checked_in', (message) => {
        const data = message.data;
        setRecentEvents(prev => [
          {
            type: 'checkin',
            message: `${data.attendee_name} checked in`,
            timestamp: new Date().toISOString(),
            data
          },
          ...prev.slice(0, 9)
        ]);
      })
    ];

    return () => unsubscribes.forEach(unsub => unsub());
  }, [onEventMessage]);

  const handleTicketUpdate = (ticketId: number, availableQuantity: number) => {
    console.log(`Ticket ${ticketId} availability updated: ${availableQuantity}`);
  };

  const isAdmin = user?.role === 'admin' || user?.role === 'organizer';

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{mockEvent.title}</h1>
              <p className="text-gray-600 mt-1">Live Event Dashboard</p>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center">
                <div 
                  className={`w-3 h-3 rounded-full mr-2 ${
                    eventConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                  }`}
                />
                <span className="text-sm text-gray-600">
                  {eventConnected ? 'Live Connected' : 'Disconnected'}
                </span>
              </div>

              <Badge 
                variant={mockEvent.status === 'active' ? 'default' : 'secondary'}
                className="px-3 py-1"
              >
                {mockEvent.status}
              </Badge>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {eventStats.totalTicketsSold}
                  </div>
                  <div className="text-sm text-gray-500">Total Tickets Sold</div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    ${eventStats.totalRevenue.toFixed(2)}
                  </div>
                  <div className="text-sm text-gray-500">Total Revenue</div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    {eventStats.conversionRate.toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-500">Conversion Rate</div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Real-time Components */}
          <div className="lg:col-span-2 space-y-6">
            {/* Live Event Stats */}
            <LiveEventStats 
              eventId={eventId} 
              className="w-full"
            />

            {/* Ticket Availability */}
            <TicketAvailability
              eventId={eventId}
              tickets={mockTickets}
              onTicketUpdate={handleTicketUpdate}
              className="w-full"
            />

            {/* Recent Activity Feed */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
              </CardHeader>
              <CardContent>
                {recentEvents.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">
                    No recent activity
                  </p>
                ) : (
                  <div className="space-y-3">
                    {recentEvents.map((event, index) => (
                      <div key={index} className="flex items-center justify-between border-b pb-3 last:border-b-0">
                        <div className="flex items-center gap-3">
                          <div className={`w-3 h-3 rounded-full ${
                            event.type === 'ticket_sold' ? 'bg-green-500' :
                            event.type === 'checkin' ? 'bg-blue-500' :
                            'bg-gray-500'
                          }`} />
                          <span className="text-sm text-gray-700">
                            {event.message}
                          </span>
                        </div>
                        <span className="text-xs text-gray-500">
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Admin Features */}
          <div className="space-y-6">
            {/* Admin Notifications (only for admin users) */}
            {isAdmin && (
              <AdminNotifications 
                className="w-full"
                maxVisible={8}
              />
            )}

            {/* Connection Status */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Connection Status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Event Updates</span>
                  <div className="flex items-center">
                    <div className={`w-2 h-2 rounded-full mr-2 ${
                      eventConnected ? 'bg-green-500' : 'bg-red-500'
                    }`} />
                    <span className="text-xs">
                      {eventConnected ? 'Connected' : 'Disconnected'}
                    </span>
                  </div>
                </div>

                {eventMessage && (
                  <div className="bg-gray-50 p-3 rounded text-xs">
                    <div className="font-medium mb-1">Last Message:</div>
                    <div className="text-gray-600">
                      Type: {eventMessage.type}
                    </div>
                    <div className="text-gray-500 mt-1">
                      {new Date(eventMessage.timestamp).toLocaleString()}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="w-full justify-start"
                  onClick={() => window.location.href = `/events/${eventId}/manage`}
                >
                  Manage Event
                </Button>
                
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="w-full justify-start"
                  onClick={() => window.location.href = `/events/${eventId}/attendees`}
                >
                  Check-in Attendees
                </Button>
                
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="w-full justify-start"
                  onClick={() => window.location.href = `/events/${eventId}/analytics`}
                >
                  View Analytics
                </Button>
              </CardContent>
            </Card>

            {/* Event Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Event Info</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <span className="font-medium text-gray-900">Location:</span>
                  <span className="text-gray-600 ml-2">{mockEvent.location}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-900">Start:</span>
                  <span className="text-gray-600 ml-2">
                    {mockEvent.startDate.toLocaleString()}
                  </span>
                </div>
                <div>
                  <span className="font-medium text-gray-900">End:</span>
                  <span className="text-gray-600 ml-2">
                    {mockEvent.endDate.toLocaleString()}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}