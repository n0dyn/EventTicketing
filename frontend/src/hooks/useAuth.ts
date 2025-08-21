import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import Cookies from 'js-cookie';

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
  token: string;
  new_password: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
}

export const useAuth = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const setAuthToken = useCallback((token: string) => {
    Cookies.set('auth_token', token, { expires: 7, secure: true });
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }, []);

  const removeAuthToken = useCallback(() => {
    Cookies.remove('auth_token');
    delete axios.defaults.headers.common['Authorization'];
  }, []);

  const login = useCallback(
    async (data: LoginData) => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await axios.post<AuthResponse>(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/login/access-token`,
          data
        );
        setAuthToken(response.data.access_token);
        
        // Get user info to determine redirect
        try {
          const userResponse = await axios.get(
            `${process.env.NEXT_PUBLIC_API_URL}/api/v1/users/me`,
            {
              headers: {
                Authorization: `Bearer ${response.data.access_token}`,
              },
            }
          );
          
          const user = userResponse.data;
          // Redirect admins to admin dashboard, regular users to user dashboard
          if (user.is_superuser) {
            router.push('/admin');
          } else {
            router.push('/dashboard');
          }
        } catch (userErr) {
          // Fallback to regular dashboard if user info fetch fails
          router.push('/dashboard');
        }
        
        return response.data;
      } catch (err) {
        if (axios.isAxiosError(err) && err.response) {
          setError(err.response.data.detail || 'Login failed');
        } else {
          setError('An unexpected error occurred');
        }
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [router, setAuthToken]
  );

  const register = useCallback(
    async (data: RegisterData) => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/register`,
          data
        );
        router.push('/auth/login?registered=true');
        return response.data;
      } catch (err) {
        if (axios.isAxiosError(err) && err.response) {
          setError(err.response.data.detail || 'Registration failed');
        } else {
          setError('An unexpected error occurred');
        }
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [router]
  );

  const logout = useCallback(() => {
    removeAuthToken();
    router.push('/auth/login');
  }, [removeAuthToken, router]);

  const forgotPassword = useCallback(
    async (data: ForgotPasswordData) => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/password-reset`,
          data
        );
        router.push('/auth/forgot-password?sent=true');
        return response.data;
      } catch (err) {
        if (axios.isAxiosError(err) && err.response) {
          setError(err.response.data.detail || 'Password reset request failed');
        } else {
          setError('An unexpected error occurred');
        }
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
        const response = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/password-reset/confirm`,
          data
        );
        router.push('/auth/login?reset=true');
        return response.data;
      } catch (err) {
        if (axios.isAxiosError(err) && err.response) {
          setError(err.response.data.detail || 'Password reset failed');
        } else {
          setError('An unexpected error occurred');
        }
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