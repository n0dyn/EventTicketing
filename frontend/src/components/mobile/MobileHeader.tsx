/**
 * Mobile Header Component
 * Responsive header optimized for mobile devices with hamburger menu
 */

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Sheet, SheetContent, SheetTrigger, SheetHeader, SheetTitle } from '../ui/sheet';
import { 
  Menu, 
  Search, 
  Bell, 
  User,
  LogOut,
  Settings,
  Ticket,
  Calendar,
  CreditCard,
  Shield,
  Home
} from 'lucide-react';

interface MobileHeaderProps {
  className?: string;
  title?: string;
  showSearch?: boolean;
  showNotifications?: boolean;
  notificationCount?: number;
}

export function MobileHeader({ 
  className = '',
  title,
  showSearch = true,
  showNotifications = true,
  notificationCount = 0
}: MobileHeaderProps) {
  const { user, isAuthenticated, logout } = useAuth();
  const router = useRouter();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    setIsMenuOpen(false);
    router.push('/');
  };

  const menuItems = [
    ...(isAuthenticated ? [
      { href: '/dashboard', icon: <Home className="w-5 h-5" />, label: 'Dashboard' },
      { href: '/dashboard/tickets', icon: <Ticket className="w-5 h-5" />, label: 'My Tickets' },
      { href: '/dashboard/orders', icon: <CreditCard className="w-5 h-5" />, label: 'Orders' },
      { href: '/dashboard/profile', icon: <User className="w-5 h-5" />, label: 'Profile' },
      { href: '/dashboard/settings', icon: <Settings className="w-5 h-5" />, label: 'Settings' },
    ] : []),
    { href: '/events', icon: <Calendar className="w-5 h-5" />, label: 'Browse Events' },
    ...(isAuthenticated && (user?.role === 'admin' || user?.role === 'organizer') ? [
      { href: '/admin', icon: <Shield className="w-5 h-5" />, label: 'Admin Panel' },
    ] : [])
  ];

  return (
    <header className={`sticky top-0 z-40 bg-white border-b border-gray-200 ${className}`}>
      <div className="flex items-center justify-between h-14 px-4">
        {/* Left side - Menu & Logo */}
        <div className="flex items-center gap-3">
          <Sheet open={isMenuOpen} onOpenChange={setIsMenuOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="sm" className="p-2">
                <Menu className="w-5 h-5" />
                <span className="sr-only">Open menu</span>
              </Button>
            </SheetTrigger>
            
            <SheetContent side="left" className="w-80 p-0">
              <div className="flex flex-col h-full">
                <SheetHeader className="p-6 border-b">
                  <div className="flex items-center gap-3">
                    {isAuthenticated && user ? (
                      <>
                        <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                          <User className="w-5 h-5 text-blue-600" />
                        </div>
                        <div className="flex-1 text-left">
                          <SheetTitle className="text-sm font-medium">
                            {user.full_name || user.email}
                          </SheetTitle>
                          <p className="text-xs text-gray-500 capitalize">
                            {user.role}
                          </p>
                        </div>
                      </>
                    ) : (
                      <SheetTitle>Menu</SheetTitle>
                    )}
                  </div>
                </SheetHeader>

                <div className="flex-1 overflow-y-auto">
                  <div className="p-4 space-y-1">
                    {menuItems.map((item) => (
                      <Link
                        key={item.href}
                        href={item.href}
                        className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                        onClick={() => setIsMenuOpen(false)}
                      >
                        {item.icon}
                        <span className="font-medium">{item.label}</span>
                      </Link>
                    ))}
                  </div>

                  {!isAuthenticated && (
                    <div className="p-4 border-t">
                      <div className="space-y-2">
                        <Link
                          href="/auth/login"
                          className="block"
                          onClick={() => setIsMenuOpen(false)}
                        >
                          <Button className="w-full">
                            Sign In
                          </Button>
                        </Link>
                        <Link
                          href="/auth/register"
                          className="block"
                          onClick={() => setIsMenuOpen(false)}
                        >
                          <Button variant="outline" className="w-full">
                            Sign Up
                          </Button>
                        </Link>
                      </div>
                    </div>
                  )}
                </div>

                {isAuthenticated && (
                  <div className="p-4 border-t">
                    <Button
                      variant="ghost"
                      onClick={handleLogout}
                      className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      <LogOut className="w-5 h-5 mr-3" />
                      Sign Out
                    </Button>
                  </div>
                )}
              </div>
            </SheetContent>
          </Sheet>

          <Link href="/" className="flex items-center">
            <span className="text-lg font-bold text-blue-600">
              {title || 'EventTicketing'}
            </span>
          </Link>
        </div>

        {/* Right side - Actions */}
        <div className="flex items-center gap-2">
          {showSearch && (
            <Button
              variant="ghost"
              size="sm"
              className="p-2"
              onClick={() => router.push('/search')}
            >
              <Search className="w-5 h-5" />
              <span className="sr-only">Search</span>
            </Button>
          )}

          {showNotifications && isAuthenticated && (
            <Button
              variant="ghost"
              size="sm"
              className="p-2 relative"
              onClick={() => router.push('/notifications')}
            >
              <Bell className="w-5 h-5" />
              {notificationCount > 0 && (
                <Badge 
                  variant="destructive" 
                  className="absolute -top-1 -right-1 h-5 w-5 text-xs flex items-center justify-center p-0 min-w-[20px]"
                >
                  {notificationCount > 99 ? '99+' : notificationCount}
                </Badge>
              )}
              <span className="sr-only">Notifications</span>
            </Button>
          )}

          {!isAuthenticated && (
            <Button
              size="sm"
              onClick={() => router.push('/auth/login')}
              className="hidden xs:inline-flex"
            >
              Sign In
            </Button>
          )}
        </div>
      </div>

      {/* Progress bar for loading states */}
      <div className="h-0.5 bg-gray-100">
        <div className="h-full bg-blue-600 transition-all duration-300" style={{ width: '0%' }} />
      </div>
    </header>
  );
}

export default MobileHeader;