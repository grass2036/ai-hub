/**
 * Register Page Component
 * 用户注册页面
 */

import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Eye, EyeOff, AlertCircle, CheckCircle } from 'lucide-react';

import { AuthLayout } from './layout';
import { useAuth } from '@/hooks/useAuth';
import { RegisterCredentials, User } from '@/types/auth';

// 密码强度检查
const checkPasswordStrength = (password: string) => {
  const requirements = [
    { test: password.length >= 8, text: '至少8个字符' },
    { test: /[A-Z]/.test(password), text: '包含大写字母' },
    { test: /[a-z]/.test(password), text: '包含小写字母' },
    { test: /\d/.test(password), text: '包含数字' },
    { test: /[!@#$%^&*(),.?":{}|<>]/.test(password), text: '包含特殊字符' }
  ];

  const score = requirements.filter(req => req.test).length;
  const strength = score <= 2 ? 'weak' : score <= 4 ? 'medium' : 'strong';
  const color = strength === 'weak' ? 'text-red-600' : strength === 'medium' ? 'text-yellow-600' : 'text-green-600';

  return { requirements, score, strength, color };
};

// 表单验证模式
const registerSchema = z.object({
  email: z
    .string()
    .min(1, '请输入邮箱地址')
    .email('请输入有效的邮箱地址'),
  username: z
    .string()
    .min(3, '用户名至少3个字符')
    .max(50, '用户名最多50个字符')
    .regex(/^[a-zA-Z0-9_-]+$/, '用户名只能包含字母、数字、下划线和连字符')
    .optional(),
  password: z
    .string()
    .min(8, '密码至少8个字符')
    .regex(/[A-Z]/, '密码必须包含大写字母')
    .regex(/[a-z]/, '密码必须包含小写字母')
    .regex(/\d/, '密码必须包含数字'),
  confirm_password: z
    .string()
    .min(1, '请确认密码'),
  name: z
    .string()
    .min(1, '请输入姓名')
    .max(255, '姓名最多255个字符')
    .optional(),
  agree_terms: z
    .boolean()
    .refine(val => val === true, '请同意服务条款和隐私政策')
}).refine(data => data.password === data.confirm_password, {
  message: '两次输入的密码不一致',
  path: ['confirm_password']
});

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const navigate = useNavigate();
  const { isAuthenticated, login } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [registrationError, setRegistrationError] = useState<string | null>(null);

  // 如果已经登录，重定向到仪表盘
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // 表单设置
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
    setValue,
    trigger
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: '',
      username: '',
      password: '',
      confirm_password: '',
      name: '',
      agree_terms: false
    }
  });

  const password = watch('password');
  const passwordStrength = password ? checkPasswordStrength(password) : null;

  // 注册mutation
  const registerMutation = useMutation({
    mutationFn: async (credentials: RegisterCredentials): Promise<User> => {
      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '注册失败');
      }

      return response.json();
    },
    onSuccess: (user) => {
      toast.success('注册成功！欢迎加入AI Hub');
      // 注册成功后自动登录
      login({
        access_token: 'temp_token', // 实际应该从后端获取
        refresh_token: 'temp_refresh',
        user: user
      });
      navigate('/dashboard');
    },
    onError: (error: Error) => {
      setRegistrationError(error.message);
      toast.error('注册失败，请检查输入信息');
    }
  });

  // 处理表单提交
  const onSubmit = (data: RegisterFormData) => {
    setRegistrationError(null);

    const credentials: RegisterCredentials = {
      email: data.email,
      username: data.username,
      password: data.password,
      name: data.name
    };

    registerMutation.mutate(credentials);
  };

  // 处理社交注册
  const handleSocialRegister = (provider: string) => {
    // TODO: 实现社交注册
    toast.info(`${provider}注册功能开发中`);
  };

  // 实时验证邮箱
  const checkEmailAvailability = async (email: string) => {
    // TODO: 实现邮箱可用性检查
    // const response = await fetch(`/api/v1/auth/check-email?email=${email}`);
    // return response.json();
    return true;
  };

  // 实时验证用户名
  const checkUsernameAvailability = async (username: string) => {
    // TODO: 实现用户名可用性检查
    // const response = await fetch(`/api/v1/auth/check-username?username=${username}`);
    // return response.json();
    return true;
  };

  return (
    <AuthLayout
      title="创建账户"
      description="加入AI Hub，开启智能对话体验"
      backLinkText="已有账户？立即登录"
      backLinkTo="/auth/login"
    >
      <CardContent className="space-y-6">
        {/* 注册错误提示 */}
        {registrationError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{registrationError}</AlertDescription>
          </Alert>
        )}

        {/* 注册表单 */}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* 邮箱输入 */}
          <div className="space-y-2">
            <Label htmlFor="email">邮箱地址 *</Label>
            <Input
              id="email"
              type="email"
              placeholder="请输入邮箱地址"
              {...register('email')}
              disabled={registerMutation.isPending}
              className={errors.email ? 'border-red-500' : ''}
            />
            {errors.email && (
              <p className="text-sm text-red-600">{errors.email.message}</p>
            )}
          </div>

          {/* 用户名输入 */}
          <div className="space-y-2">
            <Label htmlFor="username">用户名（可选）</Label>
            <Input
              id="username"
              type="text"
              placeholder="请输入用户名"
              {...register('username')}
              disabled={registerMutation.isPending}
              className={errors.username ? 'border-red-500' : ''}
            />
            {errors.username && (
              <p className="text-sm text-red-600">{errors.username.message}</p>
            )}
            <p className="text-xs text-gray-500">
              用户名将作为您的唯一标识符，只能包含字母、数字、下划线和连字符
            </p>
          </div>

          {/* 姓名输入 */}
          <div className="space-y-2">
            <Label htmlFor="name">姓名（可选）</Label>
            <Input
              id="name"
              type="text"
              placeholder="请输入您的姓名"
              {...register('name')}
              disabled={registerMutation.isPending}
              className={errors.name ? 'border-red-500' : ''}
            />
            {errors.name && (
              <p className="text-sm text-red-600">{errors.name.message}</p>
            )}
          </div>

          {/* 密码输入 */}
          <div className="space-y-2">
            <Label htmlFor="password">密码 *</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="请输入密码"
                {...register('password', {
                  onChange: () => trigger('confirm_password')
                })}
                disabled={registerMutation.isPending}
                className={errors.password ? 'border-red-500 pr-10' : 'pr-10'}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                onClick={() => setShowPassword(!showPassword)}
                disabled={registerMutation.isPending}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>
            </div>
            {errors.password && (
              <p className="text-sm text-red-600">{errors.password.message}</p>
            )}

            {/* 密码强度指示器 */}
            {passwordStrength && (
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">密码强度：</span>
                  <span className={`text-sm font-medium ${passwordStrength.color}`}>
                    {passwordStrength.strength === 'weak' ? '弱' :
                     passwordStrength.strength === 'medium' ? '中' : '强'}
                  </span>
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-300 ${
                        passwordStrength.strength === 'weak' ? 'bg-red-500 w-1/3' :
                        passwordStrength.strength === 'medium' ? 'bg-yellow-500 w-2/3' :
                        'bg-green-500 w-full'
                      }`}
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  {passwordStrength.requirements.map((req, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      {req.test ? (
                        <CheckCircle className="h-3 w-3 text-green-500" />
                      ) : (
                        <div className="h-3 w-3 rounded-full border border-gray-300" />
                      )}
                      <span className={`text-xs ${req.test ? 'text-green-600' : 'text-gray-500'}`}>
                        {req.text}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 确认密码输入 */}
          <div className="space-y-2">
            <Label htmlFor="confirm_password">确认密码 *</Label>
            <div className="relative">
              <Input
                id="confirm_password"
                type={showConfirmPassword ? 'text' : 'password'}
                placeholder="请再次输入密码"
                {...register('confirm_password')}
                disabled={registerMutation.isPending}
                className={errors.confirm_password ? 'border-red-500 pr-10' : 'pr-10'}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                disabled={registerMutation.isPending}
              >
                {showConfirmPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>
            </div>
            {errors.confirm_password && (
              <p className="text-sm text-red-600">{errors.confirm_password.message}</p>
            )}
          </div>

          {/* 服务条款同意 */}
          <div className="space-y-2">
            <div className="flex items-start space-x-2">
              <Checkbox
                id="agree_terms"
                checked={watch('agree_terms')}
                onCheckedChange={(checked) => setValue('agree_terms', !!checked)}
              />
              <Label htmlFor="agree_terms" className="text-sm leading-relaxed">
                我已阅读并同意
                <Link to="/terms" className="text-indigo-600 hover:text-indigo-500 mx-1">
                  服务条款
                </Link>
                和
                <Link to="/privacy" className="text-indigo-600 hover:text-indigo-500 mx-1">
                  隐私政策
                </Link>
              </Label>
            </div>
            {errors.agree_terms && (
              <p className="text-sm text-red-600">{errors.agree_terms.message}</p>
            )}
          </div>

          {/* 注册按钮 */}
          <Button
            type="submit"
            className="w-full"
            disabled={registerMutation.isPending}
          >
            {registerMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                注册中...
              </>
            ) : (
              '创建账户'
            )}
          </Button>
        </form>

        {/* 分隔线 */}
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <Separator className="w-full" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="bg-background px-2 text-muted-foreground">
              或使用以下方式注册
            </span>
          </div>
        </div>

        {/* 社交注册按钮 */}
        <div className="grid grid-cols-2 gap-3">
          <Button
            variant="outline"
            onClick={() => handleSocialRegister('Google')}
            disabled={registerMutation.isPending}
            className="w-full"
          >
            <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                fill="#4285F4"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#34A853"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                fill="#FBBC05"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              />
            </svg>
            Google
          </Button>
          <Button
            variant="outline"
            onClick={() => handleSocialRegister('GitHub')}
            disabled={registerMutation.isPending}
            className="w-full"
          >
            <svg className="mr-2 h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
            GitHub
          </Button>
        </div>

        {/* 注册提示 */}
        <div className="text-xs text-gray-500 dark:text-gray-400">
          <p>注册后，我们将向您的邮箱发送验证邮件，请及时验证。</p>
        </div>
      </CardContent>
    </AuthLayout>
  );
}