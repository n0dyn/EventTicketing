import React from 'react'
import { renderHook, act } from '@testing-library/react'
import { useAuth } from '@/hooks/useAuth'
import { AuthProvider } from '@/context/AuthContext'

// Mock the API client
jest.mock('@/lib/api/client', () => ({
  post: jest.fn(),
  get: jest.fn(),
}))

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
)

describe('useAuth Hook', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
    jest.clearAllMocks()
  })

  it('should initialize with no user', () => {
    const { result } = renderHook(() => useAuth(), { wrapper })
    
    expect(result.current.user).toBeNull()
    expect(result.current.isLoading).toBe(false)
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('should handle login successfully', async () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      full_name: 'Test User',
    }
    
    const mockApiResponse = {
      access_token: 'mock-token',
      token_type: 'bearer',
      user: mockUser,
    }

    const { post } = require('@/lib/api/client')
    post.mockResolvedValueOnce({ data: mockApiResponse })

    const { result } = renderHook(() => useAuth(), { wrapper })

    await act(async () => {
      await result.current.login('test@example.com', 'password')
    })

    expect(result.current.user).toEqual(mockUser)
    expect(result.current.isAuthenticated).toBe(true)
    expect(localStorage.getItem('token')).toBe('mock-token')
  })

  it('should handle login failure', async () => {
    const { post } = require('@/lib/api/client')
    post.mockRejectedValueOnce({
      response: {
        data: { detail: 'Invalid credentials' }
      }
    })

    const { result } = renderHook(() => useAuth(), { wrapper })

    await act(async () => {
      try {
        await result.current.login('wrong@example.com', 'wrongpassword')
      } catch (error) {
        // Expected to throw
      }
    })

    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('should handle logout', async () => {
    // First login
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      full_name: 'Test User',
    }
    
    localStorage.setItem('token', 'mock-token')
    localStorage.setItem('user', JSON.stringify(mockUser))

    const { result } = renderHook(() => useAuth(), { wrapper })

    act(() => {
      result.current.logout()
    })

    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('user')).toBeNull()
  })

  it('should restore user from localStorage on mount', () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      full_name: 'Test User',
    }

    localStorage.setItem('token', 'mock-token')
    localStorage.setItem('user', JSON.stringify(mockUser))

    const { result } = renderHook(() => useAuth(), { wrapper })

    expect(result.current.user).toEqual(mockUser)
    expect(result.current.isAuthenticated).toBe(true)
  })
})