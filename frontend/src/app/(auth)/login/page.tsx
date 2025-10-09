'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import AuthForm from '@/components/auth/AuthForm';

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  // 检查是否已经登录
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (token) {
          apiClient.setToken(token);
          // 验证token是否有效
          await apiClient.getCurrentUser();
          router.push('/dashboard');
        }
      } catch (error) {
        // Token无效，清除它
        localStorage.removeItem('access_token');
      }
    };

    checkAuth();
  }, [router]);

  const handleSubmit = async (data: any) => {
    setError('');
    setLoading(true);

    try {
      const response: any = await apiClient.login(data.email, data.password);

      // 设置token
      apiClient.setToken(response.access_token);

      // 记住登录状态
      if (rememberMe) {
        localStorage.setItem('remember_email', data.email);
        localStorage.setItem('remember_login', 'true');
      } else {
        localStorage.removeItem('remember_email');
        localStorage.removeItem('remember_login');
      }

      console.log('登录成功!', response.user);

      // 跳转到dashboard
      router.push('/dashboard');
    } catch (err: any) {
      console.error('登录失败:', err);

      // 根据错误类型显示不同的错误信息
      if (err.message?.includes('Invalid credentials')) {
        setError('邮箱或密码错误，请检查后重试');
      } else if (err.message?.includes('User not found')) {
        setError('该邮箱尚未注册，请先注册账户');
      } else if (err.message?.includes('Account suspended')) {
        setError('账户已被暂停，请联系客服');
      } else if (err.message?.includes('Network error') || err.message?.includes('fetch')) {
        setError('网络连接失败，请检查网络后重试');
      } else {
        setError(err.message || '登录失败，请稍后重试');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthForm
      type="login"
      onSubmit={handleSubmit}
      loading={loading}
      error={error}
      rememberMe={rememberMe}
      onRememberMeChange={setRememberMe}
    />
  );
}