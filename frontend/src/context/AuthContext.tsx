import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient, getTokens, setTokens, clearTokens } from '@/lib/api/client';

interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  role?: string;
  is_active: boolean;
  is_staff?: boolean;
  is_organizer?: boolean;
  is_admin?: boolean;
  created_at?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  checkAuth: () => Promise<void>;
  setUser: (user: User | null) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, firstName: string, lastName: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  checkAuth: async () => {},
  setUser: () => {},
  login: async () => {},
  register: async () => {},
  logout: async () => {},
});

export const useAuthContext = () => useContext(AuthContext);
export const useAuth = () => useContext(AuthContext); // Alias for compatibility

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const checkAuth = async () => {
    setIsLoading(true);
    const tokens = getTokens();
    
    if (!tokens) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    
    try {
      const response = await apiClient.get<User>('/api/v1/auth/me/');
      setUser(response.data);
    } catch (error) {
      console.error('Auth check failed:', error);
      clearTokens();
      setUser(null);
      
      // Redirect to login page if on a protected route
      if (typeof window !== 'undefined') {
        const pathname = window.location.pathname;
        if (pathname !== '/auth/login' && 
            pathname !== '/auth/register' && 
            pathname !== '/auth/forgot-password' && 
            !pathname.startsWith('/auth/reset-password')) {
          router.push('/auth/login');
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    try {
      const response = await apiClient.post('/api/v1/auth/login/', {
        email,
        password,
      });

      const { access, refresh, user: userData } = response.data;
      setTokens({ access, refresh });
      setUser(userData);
      
      // Redirect to dashboard
      router.push('/dashboard');
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const register = async (email: string, firstName: string, lastName: string, password: string) => {
    try {
      const response = await apiClient.post('/api/v1/auth/register/', {
        email,
        first_name: firstName,
        last_name: lastName,
        password,
        password_confirm: password,
      });

      const { access, refresh, user: userData } = response.data;
      setTokens({ access, refresh });
      setUser(userData);
      
      // Redirect to dashboard
      router.push('/dashboard');
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      // Call logout endpoint if needed
      await apiClient.post('/api/v1/auth/logout/', {
        refresh: getTokens()?.refresh,
      }).catch(() => {
        // Logout endpoint might not exist yet, but we can still clear tokens
      });
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      clearTokens();
      setUser(null);
      router.push('/auth/login');
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
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}; 