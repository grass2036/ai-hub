'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import AuthForm from '@/components/auth/AuthForm';

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (data: any) => {
    setError('');
    setLoading(true);

    try {
      const response: any = await apiClient.login(data.email, data.password);
      apiClient.setToken(response.access_token);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Login failed');
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
    />
  );
}