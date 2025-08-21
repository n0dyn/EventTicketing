import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import Cookies from 'js-cookie';

interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  is_active: boolean;
  is_superuser: boolean;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  checkAuth: () => Promise<void>;
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  checkAuth: async () => {},
  setUser: () => {},
});

export const useAuthContext = () => useContext(AuthContext);
export const useAuth = () => useContext(AuthContext); // Alias for compatibility

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const checkAuth = async () => {
    setIsLoading(true);
    const token = Cookies.get('auth_token');
    
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    
    try {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      const response = await axios.get<User>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/users/me`
      );
      setUser(response.data);
    } catch (error) {
      console.error('Auth check failed:', error);
      Cookies.remove('auth_token');
      delete axios.defaults.headers.common['Authorization'];
      setUser(null);
      
      // Redirect to login page if on a protected route
      const pathname = window.location.pathname;
      if (pathname !== '/auth/login' && 
          pathname !== '/auth/register' && 
          pathname !== '/auth/forgot-password' && 
          !pathname.startsWith('/auth/reset-password')) {
        router.push('/auth/login');
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const value = {
    user,
    isLoading,
    isAuthenticated: !!user,
    checkAuth,
    setUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}; 