import React from 'react';
import Link from 'next/link';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';


// 密码强度指示器组件
const PasswordStrengthIndicator = ({ password }: { password: string }) => {
  const getStrength = (password: string): { level: number; text: string; color: string } => {
    if (!password) return { level: 0, text: '', color: '' };

    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
    if (/\d/.test(password)) score++;
    if (/[^a-zA-Z\d]/.test(password)) score++;

    const levels = [
      { level: 0, text: '', color: '' },
      { level: 1, text: '弱', color: 'bg-red-500' },
      { level: 2, text: '一般', color: 'bg-yellow-500' },
      { level: 3, text: '中等', color: 'bg-blue-500' },
      { level: 4, text: '强', color: 'bg-green-500' },
      { level: 5, text: '很强', color: 'bg-green-600' }
    ];

    return levels[score] || levels[0];
  };

  const strength = getStrength(password);

  return (
    <div className="mt-2">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-gray-600">密码强度</span>
        {strength.text && (
          <span className={`text-xs font-medium ${
            strength.color.includes('red') ? 'text-red-600' :
            strength.color.includes('yellow') ? 'text-yellow-600' :
            strength.color.includes('blue') ? 'text-blue-600' :
            'text-green-600'
          }`}>
            {strength.text}
          </span>
        )}
      </div>
      <div className="w-full bg-gray-200 rounded-full h-1.5">
        <div
          className={`h-1.5 rounded-full transition-all duration-300 ${strength.color}`}
          style={{ width: `${(strength.level / 5) * 100}%` }}
        />
      </div>
    </div>
  );
};

interface AuthFormProps {
  type: 'login' | 'register';
  onSubmit: (data: any) => void;
  loading: boolean;
  error: string;
  rememberMe?: boolean;
  onRememberMeChange?: (remember: boolean) => void;
}

export default function AuthForm({ type, onSubmit, loading, error, rememberMe, onRememberMeChange }: AuthFormProps) {
  const [formData, setFormData] = React.useState({
    email: '',
    password: '',
    confirmPassword: '',
    fullName: '',
  });
  const [formErrors, setFormErrors] = React.useState<Record<string, string>>({});
  const [showPassword, setShowPassword] = React.useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = React.useState(false);
  const [touchedFields, setTouchedFields] = React.useState<Record<string, boolean>>({});

  // 初始化时检查是否有记住的邮箱
  React.useEffect(() => {
    if (type === 'login') {
      const rememberedEmail = localStorage.getItem('remember_email');
      if (rememberedEmail) {
        setFormData(prev => ({ ...prev, email: rememberedEmail }));
      }
    }
  }, [type]);

  // 处理字段失焦
  const handleFieldBlur = (field: string) => {
    setTouchedFields(prev => ({ ...prev, [field]: true }));
    // 实时验证单个字段
    validateSingleField(field);
  };

  // 验证单个字段
  const validateSingleField = (field: string) => {
    const errors: Record<string, string> = {};

    switch (field) {
      case 'email':
        if (!formData.email) {
          errors.email = '邮箱地址不能为空';
        } else if (!validateEmail(formData.email)) {
          errors.email = '请输入有效的邮箱地址';
        } else if (formData.email.length > 254) {
          errors.email = '邮箱地址过长';
        }
        break;
      case 'fullName':
        if (type === 'register') {
          if (!formData.fullName.trim()) {
            errors.fullName = '姓名不能为空';
          } else if (formData.fullName.trim().length < 2) {
            errors.fullName = '姓名至少需要2个字符';
          } else if (formData.fullName.trim().length > 50) {
            errors.fullName = '姓名过长，最多50个字符';
          }
        }
        break;
      case 'password':
        if (!formData.password) {
          errors.password = '密码不能为空';
        } else if (!validatePassword(formData.password)) {
          errors.password = '密码至少需要8个字符';
        }
        break;
      case 'confirmPassword':
        if (type === 'register' && formData.password && formData.password !== formData.confirmPassword) {
          errors.confirmPassword = '两次输入的密码不一致';
        }
        break;
    }

    setFormErrors(prev => ({ ...prev, ...errors }));
  };

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const validatePassword = (password: string): boolean => {
    return password.length >= 8;
  };

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    // 邮箱验证
    if (!formData.email) {
      errors.email = '邮箱地址不能为空';
    } else if (!validateEmail(formData.email)) {
      errors.email = '请输入有效的邮箱地址';
    } else if (formData.email.length > 254) {
      errors.email = '邮箱地址过长';
    }

    // 姓名验证 (仅注册时)
    if (type === 'register') {
      if (!formData.fullName.trim()) {
        errors.fullName = '姓名不能为空';
      } else if (formData.fullName.trim().length < 2) {
        errors.fullName = '姓名至少需要2个字符';
      } else if (formData.fullName.trim().length > 50) {
        errors.fullName = '姓名过长，最多50个字符';
      } else if (!/^[\u4e00-\u9fa5a-zA-Z\s]+$/.test(formData.fullName.trim())) {
        errors.fullName = '姓名只能包含中文、英文和空格';
      }
    }

    // 密码验证
    if (!formData.password) {
      errors.password = '密码不能为空';
    } else if (!validatePassword(formData.password)) {
      errors.password = '密码至少需要8个字符';
    } else if (formData.password.length > 128) {
      errors.password = '密码过长，最多128个字符';
    } else if (type === 'register' && formData.password.toLowerCase().includes(formData.email.toLowerCase().split('@')[0])) {
      errors.password = '密码不能包含邮箱用户名部分';
    }

    // 确认密码验证 (仅注册时)
    if (type === 'register') {
      if (!formData.confirmPassword) {
        errors.confirmPassword = '请确认密码';
      } else if (formData.password !== formData.confirmPassword) {
        errors.confirmPassword = '两次输入的密码不一致';
      }
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validateForm()) {
      onSubmit(formData);
    }
  };

  const handleChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // 清除对应字段的错误信息
    if (formErrors[field]) {
      setFormErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 sm:max-w-lg bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 bg-blue-600 rounded-lg flex items-center justify-center mb-4">
            <span className="text-white font-bold text-xl">AI</span>
          </div>
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            {type === 'login' ? '登录到 AI Hub' : '注册 AI Hub 账户'}
          </h2>
          <p className="text-gray-600">
            {type === 'login' ? '还没有账户?' : '已有账户?'}{' '}
            <Link
              href={type === 'login' ? '/register' : '/login'}
              className="font-medium text-blue-600 hover:text-blue-500 transition-colors duration-200"
            >
              {type === 'login' ? '立即注册' : '立即登录'}
            </Link>
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit} noValidate>
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
                onBlur={() => handleFieldBlur('fullName')}
                placeholder="请输入您的姓名"
                error={formErrors.fullName && touchedFields.fullName ? formErrors.fullName : ''}
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
              onBlur={() => handleFieldBlur('email')}
              placeholder="请输入您的邮箱地址"
              error={formErrors.email && touchedFields.email ? formErrors.email : ''}
            />
            <div>
              <div className="relative">
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  label="密码"
                  required
                  value={formData.password}
                  onChange={(e) => handleChange('password', e.target.value)}
                  onBlur={() => handleFieldBlur('password')}
                  placeholder="请输入至少8位密码"
                  error={formErrors.password && touchedFields.password ? formErrors.password : ''}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 focus:outline-none"
                  style={{ top: '1.5rem' }}
                >
                  {showPassword ? (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
              {type === 'register' && (
                <PasswordStrengthIndicator password={formData.password} />
              )}
            </div>
            {type === 'register' && (
              <div className="relative">
                <Input
                  id="confirm-password"
                  name="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  label="确认密码"
                  required
                  value={formData.confirmPassword}
                  onChange={(e) => handleChange('confirmPassword', e.target.value)}
                  onBlur={() => handleFieldBlur('confirmPassword')}
                  placeholder="请再次输入密码"
                  error={formErrors.confirmPassword && touchedFields.confirmPassword ? formErrors.confirmPassword : ''}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 focus:outline-none"
                  style={{ top: '1.5rem' }}
                >
                  {showConfirmPassword ? (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* 记住登录状态 - 仅在登录时显示 */}
          {type === 'login' && onRememberMeChange && (
            <div className="flex items-center">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                checked={rememberMe || false}
                onChange={(e) => onRememberMeChange(e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-700">
                记住登录状态
              </label>
            </div>
          )}

          <div className="space-y-3">
            <Button
              type="submit"
              disabled={loading || (type === 'register' && (!formData.email || !formData.password || !formData.confirmPassword || !formData.fullName))}
              isLoading={loading}
              fullWidth
              className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition-all duration-200 transform hover:scale-[1.02] focus:scale-[0.98]"
            >
              {loading ? (type === 'login' ? '登录中...' : '注册中...') : (type === 'login' ? '登录' : '注册')}
            </Button>

            {/* 快速登录选项 */}
            {type === 'login' && (
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-500">或者</span>
                </div>
              </div>
            )}
          </div>

          {type === 'register' && (
            <div className="text-xs text-gray-500 space-y-1">
              <p>• 密码至少8个字符，建议包含大小写字母、数字和特殊字符</p>
              <p>• 注册成功后将自动跳转到控制台</p>
              <p>• 如有问题，请联系客服支持</p>
            </div>
          )}

          {type === 'login' && (
            <div className="text-xs text-gray-500 space-y-1">
              <p>• 请输入您注册时使用的邮箱和密码</p>
              <p>• 记住登录状态将在下次访问时自动填充邮箱</p>
              <p>• 忘记密码请联系客服重置</p>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}