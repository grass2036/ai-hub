/**
 * Authentication Types
 * 认证相关的类型定义
 */

export interface User {
  id: string;
  email: string;
  username?: string;
  name?: string;
  avatar_url?: string;
  is_active: boolean;
  is_verified: boolean;
  is_premium: boolean;
  two_factor_enabled: boolean;
  last_login_at?: string;
  last_login_ip?: string;
  login_count: number;
  phone?: string;
  company?: string;
  website?: string;
  timezone: string;
  language: string;
  created_at: string;
  updated_at: string;
  settings: Record<string, any>;
}

export interface LoginCredentials {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterCredentials {
  email: string;
  username?: string;
  password: string;
  name?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  refresh_expires_in: number;
  user: User;
}

export interface RegisterResponse {
  user: User;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirm {
  token: string;
  new_password: string;
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
}

export interface UserUpdate {
  name?: string;
  username?: string;
  avatar_url?: string;
  phone?: string;
  company?: string;
  website?: string;
  timezone?: string;
  language?: string;
  settings?: Record<string, any>;
}

export interface TwoFactorSetup {
  secret: string;
  qr_code: string;
  backup_codes: string[];
}

export interface TwoFactorVerify {
  code: string;
}

export interface UserSession {
  id: string;
  device_type: string;
  browser: string;
  browser_version: string;
  os: string;
  os_version: string;
  ip_address: string;
  country?: string;
  region?: string;
  city?: string;
  created_at: string;
  last_activity_at: string;
  expires_at: string;
  is_active: boolean;
  termination_reason?: string;
}

export interface UserActivity {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  description: string;
  ip_address: string;
  user_agent?: string;
  endpoint?: string;
  method?: string;
  status: string;
  error_message?: string;
  created_at: string;
}

export interface UserPreferences {
  timezone: string;
  language: string;
  email_notifications: boolean;
  theme: 'light' | 'dark' | 'system';
  settings: Record<string, any>;
}

export interface ApiKey {
  id: string;
  key_id: string;
  name: string;
  permissions: string[];
  status: string;
  created_at: string;
  expires_at?: string;
  last_used_at?: string;
  usage_count: number;
  rate_limit: number;
  monthly_quota?: number;
  metadata: Record<string, any>;
}

export interface ApiKeyUsageStats {
  period_days: number;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  average_response_time: number;
  most_used_endpoints: Array<{
    endpoint: string;
    count: number;
  }>;
  daily_usage: Array<{
    date: string;
    requests: number;
  }>;
}

// API响应类型
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  errors?: Record<string, string[]>;
}

// 分页响应类型
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
  has_prev: boolean;
}