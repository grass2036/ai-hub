'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import AuthForm from '@/components/auth/AuthForm';

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (data: any) => {
    setError('');
    setLoading(true);

    try {
      const response: any = await apiClient.register(data.email, data.password, data.fullName);
      apiClient.setToken(response.access_token);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthForm 
      type="register" 
      onSubmit={handleSubmit} 
      loading={loading} 
      error={error} 
    />
  );
}