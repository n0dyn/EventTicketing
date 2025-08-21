/**
 * Mobile Navigation Component
 * Bottom navigation optimized for mobile devices
 */

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '../../hooks/useAuth';
import { Badge } from '../ui/badge';
import { 
  Home, 
  Calendar, 
  Ticket, 
  User, 
  Settings,
  Bell,
  Search,
  Plus
} from 'lucide-react';

interface NavigationItem {
  href: string;
  icon: React.ReactNode;
  label: string;
  badge?: number;
  requiresAuth?: boolean;
  adminOnly?: boolean;
}

interface MobileNavigationProps {
  className?: string;
}

export function MobileNavigation({ className = '' }: MobileNavigationProps) {
  const pathname = usePathname();
  const { user, isAuthenticated } = useAuth();

  const navigationItems: NavigationItem[] = [
    {
      href: '/',
      icon: <Home className="w-5 h-5" />,
      label: 'Home'
    },
    {
      href: '/events',
      icon: <Search className="w-5 h-5" />,
      label: 'Explore'
    },
    {
      href: '/dashboard',
      icon: <Ticket className="w-5 h-5" />,
      label: 'Tickets',
      requiresAuth: true
    },
    ...(isAuthenticated && (user?.role === 'admin' || user?.role === 'organizer') ? [{
      href: '/events/create',
      icon: <Plus className="w-5 h-5" />,
      label: 'Create',
      requiresAuth: true
    }] : []),
    {
      href: isAuthenticated ? '/dashboard/profile' : '/auth/login',
      icon: <User className="w-5 h-5" />,
      label: isAuthenticated ? 'Profile' : 'Login'
    }
  ];

  const visibleItems = navigationItems.filter(item => {
    if (item.requiresAuth && !isAuthenticated) return false;
    if (item.adminOnly && (!user || (user.role !== 'admin' && user.role !== 'organizer'))) return false;
    return true;
  });

  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === '/';
    }
    return pathname.startsWith(href);
  };

  return (
    <nav className={`fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-40 ${className}`}>
      <div className="flex">
        {visibleItems.map((item, index) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex-1 flex flex-col items-center justify-center py-2 px-1 min-h-[60px] transition-colors ${
              isActive(item.href)
                ? 'text-blue-600 bg-blue-50'
                : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
            }`}
          >
            <div className="relative">
              {item.icon}
              {item.badge && item.badge > 0 && (
                <Badge 
                  variant="destructive" 
                  className="absolute -top-2 -right-2 h-5 w-5 text-xs flex items-center justify-center p-0 min-w-[20px]"
                >
                  {item.badge > 99 ? '99+' : item.badge}
                </Badge>
              )}
            </div>
            <span className="text-xs mt-1 font-medium">{item.label}</span>
          </Link>
        ))}
      </div>
      
      {/* Safe area for devices with home indicator */}
      <div className="h-safe-area-inset-bottom bg-white"></div>
    </nav>
  );
}

export default MobileNavigation;