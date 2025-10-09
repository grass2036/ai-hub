export interface User {
  id: number;
  email: string;
  full_name?: string;
  plan: string;
  monthly_quota: number;
  quota_used: number;
  quota_remaining: number;
  is_active: boolean;
  created_at: string;
}

export interface APIKey {
  id: number;
  key_prefix: string;
  name: string;
  description?: string;
  is_active: boolean;
  rate_limit?: number;
  total_requests: number;
  last_used_at?: string;
  created_at: string;
  expires_at?: string;
  is_expired: boolean;
}

export interface UsageStats {
  quota_used: number;
  quota_total: number;
  quota_remaining: number;
  quota_percentage: number;
  quota_reset_at: string;
  days_until_reset: number;
  plan: string;
  requests_today: number;
  total_cost: number;
}