'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { getStoredItem, setStoredItem } from '@/utils/storage';

// 支持的语言
export type Language = 'zh-CN' | 'zh-TW' | 'en-US' | 'ja-JP' | 'ko-KR' | 'es-ES' | 'fr-FR' | 'de-DE' | 'ru-RU' | 'pt-BR';

// 语言配置
export const languages: Record<Language, {
  name: string;
  nativeName: string;
  flag: string;
  rtl: boolean;
  dateFormat: string;
  timeFormat: '12h' | '24h';
  currency: string;
  numberFormat: Intl.NumberFormatOptions;
}> = {
  'zh-CN': {
    name: 'Chinese (Simplified)',
    nativeName: '简体中文',
    flag: '🇨🇳',
    rtl: false,
    dateFormat: 'YYYY-MM-DD',
    timeFormat: '24h',
    currency: 'CNY',
    numberFormat: { style: 'decimal', minimumFractionDigits: 2 }
  },
  'zh-TW': {
    name: 'Chinese (Traditional)',
    nativeName: '繁體中文',
    flag: '🇹🇼',
    rtl: false,
    dateFormat: 'YYYY/MM/DD',
    timeFormat: '24h',
    currency: 'TWD',
    numberFormat: { style: 'decimal', minimumFractionDigits: 0 }
  },
  'en-US': {
    name: 'English (US)',
    nativeName: 'English',
    flag: '🇺🇸',
    rtl: false,
    dateFormat: 'MM/DD/YYYY',
    timeFormat: '12h',
    currency: 'USD',
    numberFormat: { style: 'decimal', minimumFractionDigits: 2 }
  },
  'ja-JP': {
    name: 'Japanese',
    nativeName: '日本語',
    flag: '🇯🇵',
    rtl: false,
    dateFormat: 'YYYY/MM/DD',
    timeFormat: '24h',
    currency: 'JPY',
    numberFormat: { style: 'decimal', minimumFractionDigits: 0 }
  },
  'ko-KR': {
    name: 'Korean',
    nativeName: '한국어',
    flag: '🇰🇷',
    rtl: false,
    dateFormat: 'YYYY. MM. DD.',
    timeFormat: '24h',
    currency: 'KRW',
    numberFormat: { style: 'decimal', minimumFractionDigits: 0 }
  },
  'es-ES': {
    name: 'Spanish',
    nativeName: 'Español',
    flag: '🇪🇸',
    rtl: false,
    dateFormat: 'DD/MM/YYYY',
    timeFormat: '24h',
    currency: 'EUR',
    numberFormat: { style: 'decimal', minimumFractionDigits: 2 }
  },
  'fr-FR': {
    name: 'French',
    nativeName: 'Français',
    flag: '🇫🇷',
    rtl: false,
    dateFormat: 'DD/MM/YYYY',
    timeFormat: '24h',
    currency: 'EUR',
    numberFormat: { style: 'decimal', minimumFractionDigits: 2 }
  },
  'de-DE': {
    name: 'German',
    nativeName: 'Deutsch',
    flag: '🇩🇪',
    rtl: false,
    dateFormat: 'DD.MM.YYYY',
    timeFormat: '24h',
    currency: 'EUR',
    numberFormat: { style: 'decimal', minimumFractionDigits: 2 }
  },
  'ru-RU': {
    name: 'Russian',
    nativeName: 'Русский',
    flag: '🇷🇺',
    rtl: false,
    dateFormat: 'DD.MM.YYYY',
    timeFormat: '24h',
    currency: 'RUB',
    numberFormat: { style: 'decimal', minimumFractionDigits: 2 }
  },
  'pt-BR': {
    name: 'Portuguese (Brazil)',
    nativeName: 'Português',
    flag: '🇧🇷',
    rtl: false,
    dateFormat: 'DD/MM/YYYY',
    timeFormat: '24h',
    currency: 'BRL',
    numberFormat: { style: 'decimal', minimumFractionDigits: 2 }
  }
};

// 翻译资源类型
export type TranslationKey =
  | 'common'
  | 'auth'
  | 'dashboard'
  | 'chat'
  | 'api'
  | 'settings'
  | 'error'
  | 'success'
  | 'navigation'
  | 'plugins'
  | 'developer'
  | 'billing'
  | 'analytics';

// 翻译资源
const translations: Record<Language, Record<TranslationKey, any>> = {};

// 加载翻译资源的函数
async function loadTranslations(lang: Language): Promise<Record<TranslationKey, any>> {
  try {
    // 动态导入翻译文件
    const translationsModule = await import(`@/locales/${lang}/index.json`);
    return translationsModule.default;
  } catch (error) {
    console.warn(`Failed to load translations for ${lang}:`, error);
    // 返回基础翻译
    return getBaseTranslations();
  }
}

// 基础翻译（回退使用）
function getBaseTranslations(): Record<TranslationKey, any> {
  return {
    common: {
      'loading': 'Loading...',
      'save': 'Save',
      'cancel': 'Cancel',
      'confirm': 'Confirm',
      'delete': 'Delete',
      'edit': 'Edit',
      'view': 'View',
      'close': 'Close',
      'search': 'Search',
      'filter': 'Filter',
      'sort': 'Sort',
      'back': 'Back',
      'next': 'Next',
      'previous': 'Previous',
      'submit': 'Submit',
      'reset': 'Reset',
      'refresh': 'Refresh',
      'download': 'Download',
      'upload': 'Upload',
      'install': 'Install',
      'uninstall': 'Uninstall',
      'enable': 'Enable',
      'disable': 'Disable',
      'active': 'Active',
      'inactive': 'Inactive',
      'online': 'Online',
      'offline': 'Offline',
      'connected': 'Connected',
      'disconnected': 'Disconnected',
      'yes': 'Yes',
      'no': 'No',
      'ok': 'OK',
      'error': 'Error',
      'warning': 'Warning',
      'info': 'Info',
      'success': 'Success',
      'failed': 'Failed'
    },
    auth: {
      'login': 'Login',
      'logout': 'Logout',
      'register': 'Register',
      'forgot_password': 'Forgot Password?',
      'remember_me': 'Remember Me',
      'email': 'Email',
      'password': 'Password',
      'confirm_password': 'Confirm Password',
      'login_error': 'Login Failed',
      'login_success': 'Login Successful',
      'logout_success': 'Logout Successful',
      'register_success': 'Registration Successful',
      'invalid_credentials': 'Invalid credentials',
      'account_created': 'Account created successfully',
      'password_reset_sent': 'Password reset email sent'
    },
    dashboard: {
      'title': 'Dashboard',
      'welcome': 'Welcome back',
      'overview': 'Overview',
      'stats': 'Statistics',
      'recent_activity': 'Recent Activity',
      'quick_actions': 'Quick Actions',
      'total_requests': 'Total Requests',
      'today_requests': 'Today\'s Requests',
      'monthly_quota': 'Monthly Quota',
      'cost_this_month': 'Cost This Month',
      'active_users': 'Active Users',
      'total_teams': 'Total Teams',
      'active_api_keys': 'Active API Keys',
      'security_alerts': 'Security Alerts'
    },
    chat: {
      'title': 'Chat',
      'send_message': 'Send Message',
      'type_message': 'Type your message...',
      'new_chat': 'New Chat',
      'chat_history': 'Chat History',
      'model': 'Model',
      'temperature': 'Temperature',
      'max_tokens': 'Max Tokens',
      'streaming': 'Streaming',
      'regenerate': 'Regenerate',
      'copy': 'Copy',
      'download': 'Download',
      'delete_chat': 'Delete Chat',
      'clear_history': 'Clear History'
    },
    api: {
      'title': 'API',
      'documentation': 'API Documentation',
      'test': 'Test API',
      'keys': 'API Keys',
      'usage': 'Usage',
      'rate_limit': 'Rate Limit',
      'endpoints': 'Endpoints',
      'methods': 'Methods',
      'parameters': 'Parameters',
      'responses': 'Responses',
      'examples': 'Examples'
    },
    settings: {
      'title': 'Settings',
      'profile': 'Profile',
      'preferences': 'Preferences',
      'security': 'Security',
      'notifications': 'Notifications',
      'language': 'Language',
      'theme': 'Theme',
      'privacy': 'Privacy',
      'account': 'Account'
    },
    error: {
      'page_not_found': 'Page Not Found',
      'server_error': 'Server Error',
      'network_error': 'Network Error',
      'access_denied': 'Access Denied',
      'validation_error': 'Validation Error',
      'unknown_error': 'Unknown Error',
      'try_again': 'Try Again',
      'contact_support': 'Contact Support'
    },
    success: {
      'operation_completed': 'Operation Completed',
      'data_saved': 'Data Saved Successfully',
      'changes_applied': 'Changes Applied',
      'file_uploaded': 'File Uploaded Successfully',
      'plugin_installed': 'Plugin Installed Successfully',
      'user_created': 'User Created Successfully'
    },
    navigation: {
      'dashboard': 'Dashboard',
      'chat': 'Chat',
      'api': 'API',
      'settings': 'Settings',
      'logout': 'Logout'
    },
    plugins: {
      'title': 'Plugins',
      'marketplace': 'Plugin Marketplace',
      'installed': 'Installed',
      'available': 'Available',
      'search': 'Search Plugins',
      'install': 'Install Plugin',
      'uninstall': 'Uninstall Plugin',
      'configure': 'Configure',
      'enable': 'Enable',
      'disable': 'Disable',
      'update': 'Update',
      'details': 'Plugin Details',
      'documentation': 'Documentation',
      'support': 'Support'
    },
    developer: {
      'title': 'Developer',
      'portal': 'Developer Portal',
      'docs': 'Documentation',
      'guides': 'Guides',
      'tutorials': 'Tutorials',
      'reference': 'Reference',
      'examples': 'Examples',
      'tools': 'Tools',
      'community': 'Community'
    },
    billing: {
      'title': 'Billing',
      'overview': 'Overview',
      'subscription': 'Subscription',
      'usage': 'Usage',
      'invoices': 'Invoices',
      'payment_methods': 'Payment Methods',
      'billing_address': 'Billing Address',
      'tax_info': 'Tax Information'
    },
    analytics: {
      'title': 'Analytics',
      'overview': 'Overview',
      'reports': 'Reports',
      'metrics': 'Metrics',
      'usage': 'Usage',
      'performance': 'Performance',
      'user_behavior': 'User Behavior',
      'conversions': 'Conversions',
      'retention': 'Retention'
    }
  };
}

// I18N Context
interface I18nContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string, params?: Record<string, any>) => string;
  formatDate: (date: Date | string) => string;
  formatTime: (time: Date | string) => string;
  formatNumber: (num: number) => string;
  formatCurrency: (amount: number, currency?: string) => string;
  isRTL: () => boolean;
  availableLanguages: typeof languages;
}

const I18nContext = createContext<I18nContextType | undefined>(undefined);

// I18N Provider
interface I18nProviderProps {
  children: ReactNode;
  defaultLanguage?: Language;
}

export function I18nProvider({ children, defaultLanguage = 'zh-CN' }: I18NProviderProps) {
  const [language, setLanguageState] = useState<Language>(defaultLanguage);
  const [translations, setTranslations] = useState<Record<TranslationKey, any>>({});
  const [loading, setLoading] = useState(true);

  // 检测用户语言偏好
  useEffect(() => {
    const detectUserLanguage = (): Language => {
      // 从localStorage获取保存的语言
      const savedLanguage = getStoredItem('language') as Language;
      if (savedLanguage && languages[savedLanguage]) {
        return savedLanguage;
      }

      // 从浏览器语言检测
      const browserLanguage = navigator.language;

      // 精确匹配
      if (languages[browserLanguage as Language]) {
        return browserLanguage as Language;
      }

      // 语言代码匹配
      const langCode = browserLanguage.split('-')[0] as string;
      const matchingLanguages = Object.keys(languages).filter(
        lang => lang.startsWith(langCode)
      ) as Language[];

      if (matchingLanguages.length > 0) {
        return matchingLanguages[0];
      }

      // 默认语言
      return defaultLanguage;
    };

    const detectedLanguage = detectUserLanguage();
    setLanguageState(detectedLanguage);
  }, [defaultLanguage]);

  // 加载翻译资源
  useEffect(() => {
    const loadTranslationsForLanguage = async () => {
      setLoading(true);
      try {
        const loadedTranslations = await loadTranslations(language);
        setTranslations(loadedTranslations);
      } catch (error) {
        console.error('Failed to load translations:', error);
        // 使用基础翻译作为回退
        setTranslations(getBaseTranslations());
      } finally {
        setLoading(false);
      }
    };

    loadTranslationsForLanguage();
  }, [language]);

  // 切换语言
  const changeLanguage = async (newLanguage: Language) => {
    setLanguageState(newLanguage);
    setStoredItem('language', newLanguage);

    // 保存用户偏好
    try {
      const response = await fetch('/api/v1/user/preferences', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getStoredItem('access_token')}`
        },
        body: JSON.stringify({ language: newLanguage })
      });

      if (!response.ok) {
        console.warn('Failed to save language preference');
      }
    } catch (error) {
      console.warn('Failed to save language preference:', error);
    }
  };

  // 翻译函数
  const t = (key: string, params: Record<string, any> = {}): string => {
    if (!translations || loading) return key;

    // 获取嵌套的翻译键
    const keys = key.split('.');
    let translation: any = translations;

    for (const k of keys) {
      if (translation && typeof translation === 'object' && k in translation) {
        translation = translation[k];
      } else {
        return key; // 返回原键作为回退
      }
    }

    // 处理参数替换
    if (typeof translation === 'string' && Object.keys(params).length > 0) {
      return translation.replace(/\{\{(\w+)\}/g, (match, param) => {
        return params[param] !== undefined ? String(params[param]) : match;
      });
    }

    return typeof translation === 'string' ? translation : key;
  };

  // 格式化函数
  const formatDate = (date: Date | string): string => {
    const d = typeof date === 'string' ? new Date(date) : date;
    const locale = language.replace('-', '-');
    const config = languages[language];

    try {
      // 使用语言配置的日期格式
      const options: Intl.DateTimeFormatOptions = {
        year: 'numeric',
        month: config.dateFormat.includes('MM') ? '2-digit' : 'short',
        day: '2-digit'
      };

      let formatted = new Intl.DateTimeFormat(locale, options).format(d);

      // 根据语言配置调整日期分隔符
      if (config.dateFormat === 'YYYY-MM-DD') {
        formatted = formatted.replace(/\//g, '-').replace(/\./g, '-');
      } else if (config.dateFormat === 'YYYY/MM/DD') {
        formatted = formatted.replace(/-/g, '/').replace(/\./g, '/');
      } else if (config.dateFormat === 'YYYY. MM. DD.') {
        formatted = formatted.replace(/\//g, '.').replace(/-/g, '.');
        if (!formatted.endsWith('.')) {
          formatted += '.';
        }
      }

      return formatted;
    } catch {
      // 回退到基本格式
      return d.toLocaleDateString();
    }
  };

  const formatTime = (time: Date | string): string => {
    const t = typeof time === 'string' ? new Date(time) : time;
    const locale = language.replace('-', '-');
    const config = languages[language];

    const options: Intl.DateTimeFormatOptions = {
      hour: '2-digit',
      minute: '2-digit',
      hour12: config.timeFormat === '12h'
    };

    try {
      return new Intl.DateTimeFormat(locale, options).format(t);
    } catch {
      return t.toLocaleTimeString();
    }
  };

  const formatNumber = (num: number): string => {
    const locale = language.replace('-', '-');
    const config = languages[language];

    try {
      return new Intl.NumberFormat(locale, config.numberFormat).format(num);
    } catch {
      return num.toString();
    }
  };

  const formatCurrency = (amount: number, currency?: string): string => {
    const locale = language.replace('-', '-');
    const config = languages[language];
    const targetCurrency = currency || config.currency;

    try {
      return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: targetCurrency,
        minimumFractionDigits: config.numberFormat.minimumFractionDigits,
        maximumFractionDigits: config.numberFormat.minimumFractionDigits
      }).format(amount);
    } catch {
      return `${targetCurrency} ${amount.toFixed(config.numberFormat.minimumFractionDigits || 2)}`;
    }
  };

  const isRTL = (): boolean => {
    return languages[language]?.rtl || false;
  };

  const value: I18nContextType = {
    language,
    setLanguage: changeLanguage,
    t,
    formatDate,
    formatTime,
    formatNumber,
    formatCurrency,
    isRTL,
    availableLanguages: languages
  };

  return (
    <I18nContext.Provider value={value}>
      {!loading && children}
    </I18nContext.Provider>
  );
}

// Hook for using i18n
export function useI18n(): I18nContextType {
  const context = useContext(I18nContext);
  if (context === undefined) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}

// Translation Hook with type safety
export function useTranslation() {
  const { t } = useI18n();

  return {
    t,
    // 类型安全的翻译函数
    translate: <T extends Record<string, any>>(
      key: string,
      params?: T
    ): string => t(key, params)
  };
}

// Language detection utility
export function detectBrowserLanguage(): Language {
  const browserLanguage = navigator.language;

  // 精确匹配
  if (languages[browserLanguage as Language]) {
    return browserLanguage as Language;
  }

  // 语言代码匹配
  const langCode = browserLanguage.split('-')[0];
  const matchingLanguages = Object.keys(languages).filter(
    lang => lang.startsWith(langCode)
  ) as Language[];

  return matchingLanguages.length > 0 ? matchingLanguages[0] : 'en-US';
}

// Format utility functions
export const formatRelativeTime = (date: Date | string, language: Language): string => {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  const rtf = new Intl.RelativeTimeFormat(language, {
    numeric: 'auto'
  });

  if (diffDays > 0) {
    return rtf.format(-diffDays, { unit: 'day' });
  } else if (diffHours > 0) {
    return rtf.format(-diffHours, { unit: 'hour' });
  } else if (diffMinutes > 0) {
    return rtf.format(-diffMinutes, { unit: 'minute' });
  } else {
    return rtf.format(-diffSeconds, { unit: 'second' });
  }
};

export const formatFileSize = (bytes: number, language: Language): string => {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`;
};

export default { I18nProvider, useI18n, useTranslation, languages, detectBrowserLanguage };