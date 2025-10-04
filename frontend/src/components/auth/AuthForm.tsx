import React from 'react';
import Link from 'next/link';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';

interface AuthFormProps {
  type: 'login' | 'register';
  onSubmit: (data: any) => void;
  loading: boolean;
  error: string;
}

export default function AuthForm({ type, onSubmit, loading, error }: AuthFormProps) {
  const [formData, setFormData] = React.useState({
    email: '',
    password: '',
    fullName: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const handleChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            {type === 'login' ? '登录到 AI Hub' : '注册 AI Hub 账户'}
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            {type === 'login' ? '还没有账户?' : '已有账户?'}{' '}
            <Link 
              href={type === 'login' ? '/register' : '/login'} 
              className="font-medium text-blue-600 hover:text-blue-500"
            >
              {type === 'login' ? '立即注册' : '立即登录'}
            </Link>
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <Alert variant="error" title={type === 'login' ? '登录失败' : '注册失败'}>
              {error}
            </Alert>
          )}

          <div className="space-y-4">
            {type === 'register' && (
              <Input
                id="full-name"
                name="fullName"
                type="text"
                label="姓名"
                required
                value={formData.fullName}
                onChange={(e) => handleChange('fullName', e.target.value)}
                placeholder="请输入您的姓名"
              />
            )}
            <Input
              id="email"
              name="email"
              type="email"
              label="邮箱地址"
              required
              value={formData.email}
              onChange={(e) => handleChange('email', e.target.value)}
              placeholder="请输入您的邮箱地址"
            />
            <Input
              id="password"
              name="password"
              type="password"
              label="密码"
              required
              value={formData.password}
              onChange={(e) => handleChange('password', e.target.value)}
              placeholder="请输入您的密码"
            />
          </div>

          <div>
            <Button
              type="submit"
              disabled={loading}
              isLoading={loading}
              fullWidth
            >
              {loading ? (type === 'login' ? '登录中...' : '注册中...') : (type === 'login' ? '登录' : '注册')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}