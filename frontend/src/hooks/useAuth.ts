/**
 * Authentication Hook
 * 提供认证状态管理和操作
 */

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { toast } from 'sonner';

import { User, LoginResponse } from '@/types/auth';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (response: LoginResponse, remember?: boolean) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
  refreshToken: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  // 检查是否已认证
  const isAuthenticated = !!user;

  // 初始化认证状态
  useEffect(() => {
    initializeAuth();
  }, []);

  // 自动刷新token
  useEffect(() => {
    if (!isAuthenticated) return;

    const refreshInterval = setInterval(async () => {
      const refreshed = await refreshToken();
      if (!refreshed) {
        logout();
      }
    }, 14 * 60 * 1000); // 14分钟刷新一次

    return () => clearInterval(refreshInterval);
  }, [isAuthenticated]);

  const initializeAuth = async () => {
    try {
      // 从localStorage获取token
      const accessToken = localStorage.getItem('access_token');
      const refreshToken = localStorage.getItem('refresh_token');

      if (accessToken && refreshToken) {
        // 验证token并获取用户信息
        const response = await fetch('/api/v1/auth/verify-token', {
          headers: {
            'Authorization': `Bearer ${accessToken}`
          }
        });

        if (response.ok) {
          const data = await response.json();
          setUser({
            id: data.user_id,
            email: data.email,
            name: data.name,
            username: data.username,
            is_active: true,
            is_verified: true,
            is_premium: false,
            two_factor_enabled: false,
            last_login_at: data.last_login_at,
            last_login_ip: data.last_login_ip,
            login_count: 0,
            phone: null,
            company: null,
            website: null,
            timezone: 'UTC',
            language: 'zh-CN',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            avatar_url: null,
            settings: {}
          });
        } else {
          // Token无效，尝试刷新
          const refreshed = await refreshToken();
          if (!refreshed) {
            clearTokens();
          }
        }
      }
    } catch (error) {
      console.error('认证初始化失败:', error);
      clearTokens();
    } finally {
      setIsLoading(false);
    }
  };

  const login = (response: LoginResponse, remember = false) => {
    // 保存认证信息
    if (remember) {
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('refresh_token', response.refresh_token);
    } else {
      sessionStorage.setItem('access_token', response.access_token);
      sessionStorage.setItem('refresh_token', response.refresh_token);
    }

    setUser(response.user);
    toast.success('登录成功！');
  };

  const logout = async () => {
    try {
      // 调用登出API
      const token = getAccessToken();
      if (token) {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
      }
    } catch (error) {
      console.error('登出API调用失败:', error);
    } finally {
      // 清除本地存储
      clearTokens();
      setUser(null);
      toast.success('已退出登录');

      // 重定向到登录页
      const currentPath = location.pathname;
      if (currentPath.startsWith('/auth/')) {
        navigate('/auth/login');
      } else {
        navigate('/auth/login', { state: { from: { pathname: currentPath } } });
      }
    }
  };

  const updateUser = (userData: Partial<User>) => {
    if (user) {
      const updatedUser = { ...user, ...userData };
      setUser(updatedUser);
    }
  };

  const refreshToken = async (): Promise<boolean> => {
    try {
      const refresh_token = getRefreshToken();
      if (!refresh_token) {
        return false;
      }

      const response = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ refresh_token })
      });

      if (response.ok) {
        const data: LoginResponse = await response.json();

        // 更新token
        if (localStorage.getItem('access_token')) {
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
        } else {
          sessionStorage.setItem('access_token', data.access_token);
          sessionStorage.setItem('refresh_token', data.refresh_token);
        }

        setUser(data.user);
        return true;
      } else {
        return false;
      }
    } catch (error) {
      console.error('Token刷新失败:', error);
      return false;
    }
  };

  const getAccessToken = (): string | null => {
    return localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
  };

  const getRefreshToken = (): string | null => {
    return localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
  };

  const clearTokens = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
  };

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    updateUser,
    refreshToken
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth必须在AuthProvider内部使用');
  }
  return context;
}

// HTTP请求拦截器
export function useAuthenticatedFetch() {
  const { isAuthenticated, refreshToken, logout } = useAuth();

  const authenticatedFetch = async (url: string, options: RequestInit = {}) => {
    const getAccessToken = (): string | null => {
      return localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    };

    const token = getAccessToken();
    if (token) {
      options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`
      };
    }

    try {
      const response = await fetch(url, options);

      // 如果是401错误，尝试刷新token
      if (response.status === 401 && isAuthenticated) {
        const refreshed = await refreshToken();
        if (refreshed) {
          // 重新尝试请求
          const newToken = getAccessToken();
          if (newToken) {
            options.headers = {
              ...options.headers,
              'Authorization': `Bearer ${newToken}`
            };
            return fetch(url, options);
          }
        } else {
          // 刷新失败，登出
          logout();
        }
      }

      return response;
    } catch (error) {
      console.error('认证请求失败:', error);
      throw error;
    }
  };

  return { authenticatedFetch };
}