/**
 * Swipeable Card Component
 * Touch-optimized card component with swipe gestures for mobile devices
 */

import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Trash2, Heart, Share, MoreHorizontal } from 'lucide-react';

interface SwipeAction {
  id: string;
  icon: React.ReactNode;
  label: string;
  color: string;
  backgroundColor: string;
  action: () => void;
}

interface SwipeableCardProps {
  children: React.ReactNode;
  leftActions?: SwipeAction[];
  rightActions?: SwipeAction[];
  className?: string;
  disabled?: boolean;
  threshold?: number;
  onSwipe?: (direction: 'left' | 'right', actionId?: string) => void;
}

export function SwipeableCard({
  children,
  leftActions = [],
  rightActions = [],
  className = '',
  disabled = false,
  threshold = 80,
  onSwipe
}: SwipeableCardProps) {
  const [translateX, setTranslateX] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [actionTriggered, setActionTriggered] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);
  const startPosRef = useRef({ x: 0, y: 0 });
  const currentPosRef = useRef({ x: 0, y: 0 });
  const startTimeRef = useRef(0);

  const maxSwipeDistance = 120;

  const handleStart = (clientX: number, clientY: number) => {
    if (disabled) return;
    
    setIsDragging(true);
    setActionTriggered(false);
    startPosRef.current = { x: clientX, y: clientY };
    currentPosRef.current = { x: clientX, y: clientY };
    startTimeRef.current = Date.now();
  };

  const handleMove = (clientX: number, clientY: number) => {
    if (!isDragging || disabled) return;

    const deltaX = clientX - startPosRef.current.x;
    const deltaY = clientY - startPosRef.current.y;
    
    // Check if this is more of a horizontal swipe than vertical
    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 10) {
      const clampedDelta = Math.max(-maxSwipeDistance, Math.min(maxSwipeDistance, deltaX));
      setTranslateX(clampedDelta);
      currentPosRef.current = { x: clientX, y: clientY };
      
      // Prevent scrolling when swiping horizontally
      event?.preventDefault();
    }
  };

  const handleEnd = () => {
    if (!isDragging || disabled) return;
    
    setIsDragging(false);
    
    const deltaX = currentPosRef.current.x - startPosRef.current.x;
    const deltaTime = Date.now() - startTimeRef.current;
    const velocity = Math.abs(deltaX) / deltaTime;
    
    // Determine if swipe should trigger an action
    const shouldTriggerAction = Math.abs(deltaX) > threshold || velocity > 0.5;
    
    if (shouldTriggerAction && !actionTriggered) {
      const direction = deltaX > 0 ? 'right' : 'left';
      const actions = direction === 'right' ? leftActions : rightActions;
      
      if (actions.length > 0) {
        setActionTriggered(true);
        const actionIndex = Math.min(
          Math.floor((Math.abs(deltaX) / maxSwipeDistance) * actions.length),
          actions.length - 1
        );
        const action = actions[actionIndex];
        
        // Execute action after animation
        setTimeout(() => {
          action.action();
          onSwipe?.(direction, action.id);
          setTranslateX(0);
          setActionTriggered(false);
        }, 150);
        
        return;
      }
    }
    
    // Reset position
    setTranslateX(0);
  };

  // Touch events
  const handleTouchStart = (e: React.TouchEvent) => {
    const touch = e.touches[0];
    handleStart(touch.clientX, touch.clientY);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    const touch = e.touches[0];
    handleMove(touch.clientX, touch.clientY);
  };

  const handleTouchEnd = () => {
    handleEnd();
  };

  // Mouse events (for testing)
  const handleMouseDown = (e: React.MouseEvent) => {
    handleStart(e.clientX, e.clientY);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    handleMove(e.clientX, e.clientY);
  };

  const handleMouseUp = () => {
    handleEnd();
  };

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      setTranslateX(0);
      setIsDragging(false);
      setActionTriggered(false);
    };
  }, []);

  const getActionsToShow = () => {
    if (translateX > 0) return leftActions;
    if (translateX < 0) return rightActions;
    return [];
  };

  const actionsToShow = getActionsToShow();
  const showActions = Math.abs(translateX) > 20 && actionsToShow.length > 0;

  return (
    <div className={`relative overflow-hidden ${className}`}>
      {/* Background actions */}
      {showActions && (
        <div className="absolute inset-0 flex">
          {translateX > 0 && leftActions.length > 0 && (
            <div 
              className="flex items-center justify-start pl-4"
              style={{
                width: Math.abs(translateX),
                backgroundColor: leftActions[0].backgroundColor
              }}
            >
              <div className="flex items-center gap-2">
                <span style={{ color: leftActions[0].color }}>
                  {leftActions[0].icon}
                </span>
                <span 
                  className="text-sm font-medium"
                  style={{ color: leftActions[0].color }}
                >
                  {leftActions[0].label}
                </span>
              </div>
            </div>
          )}
          
          {translateX < 0 && rightActions.length > 0 && (
            <div 
              className="flex items-center justify-end pr-4 ml-auto"
              style={{
                width: Math.abs(translateX),
                backgroundColor: rightActions[0].backgroundColor
              }}
            >
              <div className="flex items-center gap-2">
                <span 
                  className="text-sm font-medium"
                  style={{ color: rightActions[0].color }}
                >
                  {rightActions[0].label}
                </span>
                <span style={{ color: rightActions[0].color }}>
                  {rightActions[0].icon}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Main card content */}
      <div
        ref={cardRef}
        className={`transition-transform duration-200 ${isDragging ? '' : 'ease-out'}`}
        style={{
          transform: `translateX(${translateX}px)`,
          touchAction: isDragging ? 'none' : 'auto'
        }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onMouseDown={handleMouseDown}
        onMouseMove={isDragging ? handleMouseMove : undefined}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <Card className={`${isDragging ? 'shadow-lg' : ''}`}>
          <CardContent className="p-0">
            {children}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Predefined common actions
export const commonSwipeActions = {
  delete: {
    id: 'delete',
    icon: <Trash2 className="w-5 h-5" />,
    label: 'Delete',
    color: 'white',
    backgroundColor: '#ef4444',
    action: () => console.log('Delete action')
  },
  favorite: {
    id: 'favorite',
    icon: <Heart className="w-5 h-5" />,
    label: 'Favorite',
    color: 'white', 
    backgroundColor: '#ec4899',
    action: () => console.log('Favorite action')
  },
  share: {
    id: 'share',
    icon: <Share className="w-5 h-5" />,
    label: 'Share',
    color: 'white',
    backgroundColor: '#3b82f6',
    action: () => console.log('Share action')
  },
  more: {
    id: 'more',
    icon: <MoreHorizontal className="w-5 h-5" />,
    label: 'More',
    color: 'white',
    backgroundColor: '#6b7280',
    action: () => console.log('More action')
  }
};

export default SwipeableCard;