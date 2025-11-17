import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient, getTokens, setTokens, clearTokens } from '@/lib/api/client';

interface LoginData {
  email: string;
  password: string;
}

interface RegisterData {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
}

interface ForgotPasswordData {
  email: string;
}

interface ResetPasswordData {
  email: string;
  token: string;
  new_password: string;
  new_password_confirm: string;
}

interface AuthResponse {
  access: string;
  refresh: string;
  user?: {
    id: string;
    email: string;
    is_staff?: boolean;
    is_superuser?: boolean;
  };
}

export const useAuth = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const login = useCallback(
    async (data: LoginData) => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await apiClient.post<AuthResponse>(
          '/api/v1/auth/login/',
          data
        );
        
        const { access, refresh } = response.data;
        setTokens({ access, refresh });
        
        // Get user info to determine redirect
        try {
          const userResponse = await apiClient.get(
            '/api/v1/auth/me/'
          );
          
          const user = userResponse.data;
          // Redirect admins to admin dashboard, regular users to user dashboard
          if (user.is_staff || user.is_superuser) {
            router.push('/admin');
          } else {
            router.push('/dashboard');
          }
        } catch (userErr) {
          // Fallback to regular dashboard if user info fetch fails
          router.push('/dashboard');
        }
        
        return response.data;
      } catch (err: any) {
        const message = err.response?.data?.detail || err.response?.data?.email?.[0] || 'Login failed';
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [router]
  );

  const register = useCallback(
    async (data: RegisterData) => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await apiClient.post<AuthResponse>(
          '/api/v1/auth/register/',
          {
            ...data,
            password_confirm: data.password,
          }
        );
        
        const { access, refresh } = response.data;
        setTokens({ access, refresh });
        
        // Redirect to dashboard after successful registration
        router.push('/dashboard');
        return response.data;
      } catch (err: any) {
        const message = err.response?.data?.detail || 
                       err.response?.data?.email?.[0] ||
                       err.response?.data?.password?.[0] ||
                       'Registration failed';
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [router]
  );

  const logout = useCallback(async () => {
    try {
      // Call logout endpoint
      await apiClient.post('/api/v1/auth/logout/', {
        refresh: getTokens()?.refresh,
      }).catch(() => {
        // Ignore logout endpoint errors
      });
    } finally {
      clearTokens();
      router.push('/auth/login');
    }
  }, [router]);

  const forgotPassword = useCallback(
    async (data: ForgotPasswordData) => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await apiClient.post(
          '/api/v1/auth/password/reset/',
          data
        );
        router.push('/auth/forgot-password?sent=true');
        return response.data;
      } catch (err: any) {
        const message = err.response?.data?.detail || 'Password reset request failed';
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [router]
  );

  const resetPassword = useCallback(
    async (data: ResetPasswordData) => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await apiClient.post(
          '/api/v1/auth/password/reset/confirm/',
          data
        );
        router.push('/auth/login?reset=true');
        return response.data;
      } catch (err: any) {
        const message = err.response?.data?.detail || err.response?.data?.new_password?.[0] || 'Password reset failed';
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [router]
  );

  return {
    login,
    register,
    logout,
    forgotPassword,
    resetPassword,
    isLoading,
    error,
  };
};
