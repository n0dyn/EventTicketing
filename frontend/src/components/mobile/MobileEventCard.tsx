/**
 * Mobile Event Card Component
 * Optimized event card for mobile devices with touch interactions
 */

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import SwipeableCard, { commonSwipeActions } from './SwipeableCard';
import { 
  Calendar, 
  MapPin, 
  Users, 
  Heart, 
  Share, 
  Clock,
  DollarSign,
  Star
} from 'lucide-react';

interface Event {
  id: number;
  title: string;
  description: string;
  imageUrl?: string;
  startDate: string;
  endDate: string;
  location: string;
  price: number;
  availableTickets: number;
  totalTickets: number;
  category: string;
  organizer: string;
  rating?: number;
  isFavorite?: boolean;
}

interface MobileEventCardProps {
  event: Event;
  variant?: 'compact' | 'full' | 'featured';
  showSwipeActions?: boolean;
  onFavorite?: (eventId: number) => void;
  onShare?: (event: Event) => void;
  onTicketPurchase?: (eventId: number) => void;
  className?: string;
}

export function MobileEventCard({
  event,
  variant = 'compact',
  showSwipeActions = true,
  onFavorite,
  onShare,
  onTicketPurchase,
  className = ''
}: MobileEventCardProps) {
  const [imageError, setImageError] = useState(false);
  const [isPressed, setIsPressed] = useState(false);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return {
      month: date.toLocaleDateString('en-US', { month: 'short' }),
      day: date.getDate(),
      time: date.toLocaleTimeString('en-US', { 
        hour: 'numeric', 
        minute: '2-digit',
        hour12: true 
      })
    };
  };

  const startDate = formatDate(event.startDate);
  const availability = (event.availableTickets / event.totalTickets) * 100;
  const isSoldOut = event.availableTickets === 0;
  const isLowStock = availability <= 20 && !isSoldOut;

  const swipeActions = showSwipeActions ? {
    left: [
      {
        ...commonSwipeActions.favorite,
        action: () => onFavorite?.(event.id)
      }
    ],
    right: [
      {
        ...commonSwipeActions.share,
        action: () => onShare?.(event)
      }
    ]
  } : { left: [], right: [] };

  const handleTouchStart = () => setIsPressed(true);
  const handleTouchEnd = () => setIsPressed(false);

  const renderCompactCard = () => (
    <div className="flex gap-3 p-3">
      {/* Event Date */}
      <div className="flex-shrink-0 text-center bg-blue-50 rounded-lg p-2 w-16">
        <div className="text-xs font-medium text-blue-600 uppercase">
          {startDate.month}
        </div>
        <div className="text-xl font-bold text-blue-900">
          {startDate.day}
        </div>
      </div>

      {/* Event Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-semibold text-gray-900 text-sm leading-tight line-clamp-2">
            {event.title}
          </h3>
          <Button
            variant="ghost"
            size="sm"
            className="p-1 h-auto flex-shrink-0"
            onClick={() => onFavorite?.(event.id)}
          >
            <Heart className={`w-4 h-4 ${event.isFavorite ? 'fill-red-500 text-red-500' : 'text-gray-400'}`} />
          </Button>
        </div>

        <div className="mt-1 space-y-1">
          <div className="flex items-center gap-1 text-xs text-gray-600">
            <Clock className="w-3 h-3" />
            <span>{startDate.time}</span>
          </div>
          
          <div className="flex items-center gap-1 text-xs text-gray-600">
            <MapPin className="w-3 h-3" />
            <span className="truncate">{event.location}</span>
          </div>
        </div>

        <div className="mt-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              {event.category}
            </Badge>
            {isLowStock && (
              <Badge variant="destructive" className="text-xs">
                Low Stock
              </Badge>
            )}
          </div>
          
          <div className="text-right">
            <div className="text-sm font-bold text-gray-900">
              ${event.price}
            </div>
            <div className="text-xs text-gray-500">
              {event.availableTickets} left
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderFullCard = () => (
    <div>
      {/* Event Image */}
      <div className="relative aspect-video bg-gray-200 rounded-t-lg overflow-hidden">
        {event.imageUrl && !imageError ? (
          <Image
            src={event.imageUrl}
            alt={event.title}
            fill
            className="object-cover"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="flex items-center justify-center h-full bg-gradient-to-br from-blue-100 to-purple-100">
            <Calendar className="w-12 h-12 text-gray-400" />
          </div>
        )}
        
        {/* Overlay badges */}
        <div className="absolute top-2 left-2">
          <Badge className="bg-white/90 text-gray-900 backdrop-blur-sm">
            {event.category}
          </Badge>
        </div>
        
        <div className="absolute top-2 right-2 flex gap-2">
          {event.rating && (
            <Badge className="bg-yellow-500 text-white">
              <Star className="w-3 h-3 mr-1" />
              {event.rating}
            </Badge>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="p-2 bg-white/90 hover:bg-white backdrop-blur-sm rounded-full"
            onClick={() => onFavorite?.(event.id)}
          >
            <Heart className={`w-4 h-4 ${event.isFavorite ? 'fill-red-500 text-red-500' : 'text-gray-600'}`} />
          </Button>
        </div>

        {isSoldOut && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <Badge variant="destructive" className="px-4 py-2 text-sm">
              SOLD OUT
            </Badge>
          </div>
        )}
      </div>

      {/* Event Details */}
      <div className="p-4">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 text-center bg-blue-50 rounded-lg p-2 w-14">
            <div className="text-xs font-medium text-blue-600 uppercase">
              {startDate.month}
            </div>
            <div className="text-lg font-bold text-blue-900">
              {startDate.day}
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-gray-900 text-lg leading-tight line-clamp-2 mb-2">
              {event.title}
            </h3>
            
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Clock className="w-4 h-4" />
                <span>{startDate.time}</span>
              </div>
              
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <MapPin className="w-4 h-4" />
                <span className="truncate">{event.location}</span>
              </div>
              
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Users className="w-4 h-4" />
                <span>{event.organizer}</span>
              </div>
            </div>

            <p className="text-sm text-gray-600 mt-3 line-clamp-2">
              {event.description}
            </p>
          </div>
        </div>

        {/* Price and Action */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t">
          <div>
            <div className="text-2xl font-bold text-gray-900">
              ${event.price}
            </div>
            <div className="text-sm text-gray-500">
              {event.availableTickets} of {event.totalTickets} available
            </div>
          </div>
          
          <Button
            disabled={isSoldOut}
            onClick={() => onTicketPurchase?.(event.id)}
            className="px-6"
          >
            {isSoldOut ? 'Sold Out' : 'Get Tickets'}
          </Button>
        </div>

        {/* Availability Progress Bar */}
        {!isSoldOut && (
          <div className="mt-3">
            <div className="flex justify-between text-xs text-gray-600 mb-1">
              <span>Availability</span>
              <span>{Math.round(availability)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all duration-300 ${
                  isLowStock ? 'bg-red-500' : 'bg-green-500'
                }`}
                style={{ width: `${availability}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const cardContent = variant === 'compact' ? renderCompactCard() : renderFullCard();

  if (showSwipeActions) {
    return (
      <SwipeableCard
        leftActions={swipeActions.left}
        rightActions={swipeActions.right}
        className={className}
      >
        <Link href={`/events/${event.id}`}>
          <div
            className={`transition-transform duration-150 ${
              isPressed ? 'scale-95' : 'scale-100'
            }`}
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
            onMouseDown={handleTouchStart}
            onMouseUp={handleTouchEnd}
            onMouseLeave={handleTouchEnd}
          >
            {cardContent}
          </div>
        </Link>
      </SwipeableCard>
    );
  }

  return (
    <Link href={`/events/${event.id}`} className={className}>
      <Card
        className={`transition-all duration-150 hover:shadow-md active:scale-95 ${
          isPressed ? 'scale-95' : 'scale-100'
        }`}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        onMouseDown={handleTouchStart}
        onMouseUp={handleTouchEnd}
        onMouseLeave={handleTouchEnd}
      >
        <CardContent className="p-0">
          {cardContent}
        </CardContent>
      </Card>
    </Link>
  );
}

export default MobileEventCard;