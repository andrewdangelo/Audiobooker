/**
 * Auth Service
 * 
 * Handles authentication requests to the auth microservice via API proxy
 * All requests go through http://localhost:8009/auth/*
 */

import api from './api'

export interface LoginCredentials {
  email: string
  password: string
}

export interface SignupData {
  email: string
  password: string
  first_name: string
  last_name?: string
}

export interface AuthResponse {
  user: {
    id: string
    email: string
    first_name: string
    last_name?: string
    username?: string
    is_active: boolean
    auth_provider: string
  }
  access_token: string
  refresh_token: string
  token_type: string
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface UpdateProfileData {
  first_name?: string
  last_name?: string
  username?: string
}

/**
 * Auth Service class
 */
class AuthService {
  private readonly AUTH_PREFIX = '/auth'
  private readonly ACCOUNTS_PREFIX = '/auth/accounts'

  /**
   * Login with email and password
   */
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>(
      `${this.AUTH_PREFIX}/login`,
      credentials
    )
    return response.data
  }

  /**
   * Signup / Register new user
   */
  async signup(data: SignupData): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>(
      `${this.AUTH_PREFIX}/signup`,
      data
    )
    return response.data
  }

  /**
   * Get current authenticated user
   */
  async getCurrentUser(token: string): Promise<AuthResponse['user']> {
    const response = await api.get<AuthResponse['user']>(
      `${this.AUTH_PREFIX}/me`,
      {
        params: { token }
      }
    )
    return response.data
  }

  /**
   * Refresh access token
   */
  async refreshToken(refreshToken: string): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>(
      `${this.AUTH_PREFIX}/refresh`,
      { refresh_token: refreshToken }
    )
    return response.data
  }

  /**
   * Logout user
   */
  async logout(token: string, refreshToken: string): Promise<void> {
    await api.post(
      `${this.AUTH_PREFIX}/logout`,
      { refresh_token: refreshToken },
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )
  }

  /**
   * Get user profile
   */
  async getProfile(token: string): Promise<AuthResponse['user']> {
    const response = await api.get<AuthResponse['user']>(
      `${this.ACCOUNTS_PREFIX}/profile`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )
    return response.data
  }

  /**
   * Update user profile
   */
  async updateProfile(token: string, data: UpdateProfileData): Promise<AuthResponse['user']> {
    const response = await api.put<AuthResponse['user']>(
      `${this.ACCOUNTS_PREFIX}/profile`,
      data,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )
    return response.data
  }

  /**
   * Change password
   */
  async changePassword(token: string, oldPassword: string, newPassword: string): Promise<void> {
    await api.post(
      `${this.ACCOUNTS_PREFIX}/change-password`,
      {
        old_password: oldPassword,
        new_password: newPassword
      },
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )
  }

  /**
   * Get account settings
   */
  async getAccountSettings(token: string): Promise<any> {
    const response = await api.get(
      `${this.ACCOUNTS_PREFIX}/settings`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )
    return response.data
  }

  /**
   * Update account settings
   */
  async updateAccountSettings(token: string, settings: any): Promise<any> {
    const response = await api.put(
      `${this.ACCOUNTS_PREFIX}/settings`,
      settings,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )
    return response.data
  }

  /**
   * Delete account
   */
  async deleteAccount(token: string): Promise<void> {
    await api.delete(
      `${this.ACCOUNTS_PREFIX}/account`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )
  }

  /**
   * Get Google OAuth authorization URL
   */
  async getGoogleAuthUrl(): Promise<{ authorization_url: string; state: string }> {
    const response = await api.get<{ authorization_url: string; state: string }>(
      `${this.AUTH_PREFIX}/google/auth-url`
    )
    return response.data
  }

  /**
   * Google OAuth callback
   */
  async googleOAuthCallback(code: string, state?: string): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>(
      `${this.AUTH_PREFIX}/google/callback`,
      { code, state }
    )
    return response.data
  }

  /**
   * Get user credits
   */
  async getUserCredits(token: string): Promise<{ basic_credits: number; premium_credits: number; total_credits: number }> {
    const response = await api.get<{ basic_credits: number; premium_credits: number; total_credits: number }>(
      `${this.ACCOUNTS_PREFIX}/credits`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )
    return response.data
  }

  /**
   * Get user subscription status
   */
  async getSubscriptionStatus(token: string): Promise<{
    subscription_plan: 'none' | 'basic' | 'premium'
    subscription_status: 'none' | 'active' | 'cancelled' | 'expired' | 'pending_cancellation'
    subscription_billing_cycle: 'monthly' | 'annual' | null
    subscription_end_date: string | null
    subscription_discount_applied: boolean
    is_subscribed: boolean
  }> {
    const response = await api.get(
      `${this.ACCOUNTS_PREFIX}/subscription`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )
    return response.data
  }

  /**
   * Store auth tokens in localStorage
   */
  storeTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('refresh_token', refreshToken)
  }

  /**
   * Get stored access token
   */
  getAccessToken(): string | null {
    return localStorage.getItem('access_token')
  }

  /**
   * Get stored refresh token
   */
  getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token')
  }

  /**
   * Clear stored tokens
   */
  clearTokens(): void {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  /**
   * Check if user is authenticated (has valid token)
   */
  isAuthenticated(): boolean {
    return !!this.getAccessToken()
  }
}

// Export singleton instance
export const authService = new AuthService()
export default authService
