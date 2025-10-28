/**
 * 计费系统布局组件
 *
 * 提供计费系统的整体布局结构，包括导航、侧边栏等。
 */

'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  HomeIcon,
  CreditCardIcon,
  ChartBarIcon,
  DocumentTextIcon,
  CogIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  XMarkIcon,
  UserCircleIcon,
  BellIcon,
} from '@heroicons/react/24/outline';
import { BellIcon as BellSolidIcon } from '@heroicons/react/24/solid';

import { useBillingData } from '@/store/billing-store';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';

interface BillingLayoutProps {
  children: React.ReactNode;
  className?: string;
}

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<any>;
  badge?: string;
  description?: string;
}

const navigation: NavItem[] = [
  {
    name: 'Overview',
    href: '/billing',
    icon: HomeIcon,
    description: 'Billing summary and current status',
  },
  {
    name: 'Subscription',
    href: '/billing/subscription',
    icon: CreditCardIcon,
    description: 'Manage your subscription plan',
  },
  {
    name: 'Usage',
    href: '/billing/usage',
    icon: ChartBarIcon,
    description: 'View your API usage and quotas',
  },
  {
    name: 'Invoices',
    href: '/billing/invoices',
    icon: DocumentTextIcon,
    description: 'Download and manage invoices',
  },
  {
    name: 'Settings',
    href: '/billing/settings',
    icon: CogIcon,
    description: 'Configure billing preferences',
  },
];

export const BillingLayout: React.FC<BillingLayoutProps> = ({
  children,
  className,
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();
  const { currentSubscription, billingSummary } = useBillingData();

  const isActive = (href: string) => {
    if (href === '/billing') {
      return pathname === href;
    }
    return pathname.startsWith(href);
  };

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-200">
        <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-sm">AI</span>
        </div>
        <div>
          <h1 className="text-lg font-semibold text-gray-900">AI Hub</h1>
          <p className="text-xs text-gray-600">Billing Center</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {navigation.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.href);

          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors',
                active
                  ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-600'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="flex-1">{item.name}</span>
              {item.badge && (
                <Badge variant="secondary" className="text-xs">
                  {item.badge}
                </Badge>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Current Subscription Summary */}
      {currentSubscription && (
        <div className="px-4 py-4 border-t border-gray-200">
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-xs font-medium text-gray-700">
                Current Plan
              </span>
            </div>
            <div className="text-sm font-semibold text-gray-900">
              {currentSubscription.plan.type.charAt(0).toUpperCase() +
                currentSubscription.plan.type.slice(1)} Plan
            </div>
            <div className="text-xs text-gray-600 mt-1">
              {formatCurrency(currentSubscription.unitPrice)}/{currentSubscription.billingCycle}
            </div>
            {currentSubscription.daysUntilRenewal > 0 && (
              <div className="text-xs text-gray-600 mt-2">
                Renews in {currentSubscription.daysUntilRenewal} days
              </div>
            )}
          </div>
        </div>
      )}

      {/* User Actions */}
      <div className="px-4 py-4 border-t border-gray-200">
        <div className="space-y-2">
          <Button variant="ghost" className="w-full justify-start" size="sm">
            <BellIcon className="w-4 h-4 mr-2" />
            Notifications
            <Badge variant="secondary" className="ml-auto text-xs">
              3
            </Badge>
          </Button>

          <Button variant="ghost" className="w-full justify-start" size="sm">
            <UserCircleIcon className="w-4 h-4 mr-2" />
            Account Settings
          </Button>

          <Button variant="ghost" className="w-full justify-start" size="sm">
            <ArrowRightOnRectangleIcon className="w-4 h-4 mr-2" />
            Sign Out
          </Button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile Sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black bg-opacity-25 lg:hidden"
              onClick={() => setSidebarOpen(false)}
            />
            <motion.div
              initial={{ x: -300 }}
              animate={{ x: 0 }}
              exit={{ x: -300 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-0 z-50 w-72 bg-white lg:hidden"
            >
              <div className="flex items-center justify-between p-4 border-b border-gray-200">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                    <span className="text-white font-bold text-sm">AI</span>
                  </div>
                  <span className="font-semibold text-gray-900">Billing</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSidebarOpen(false)}
                >
                  <XMarkIcon className="w-5 h-5" />
                </Button>
              </div>
              <SidebarContent />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Desktop Sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-40 lg:w-72 lg:bg-white lg:border-r lg:border-gray-200">
        <SidebarContent />
      </div>

      {/* Main Content */}
      <div className="lg:pl-72">
        {/* Top Navigation */}
        <header className="sticky top-0 z-30 bg-white border-b border-gray-200">
          <div className="flex items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
            {/* Mobile Menu Button */}
            <Button
              variant="ghost"
              size="sm"
              className="lg:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <Bars3Icon className="w-5 h-5" />
            </Button>

            {/* Breadcrumb */}
            <div className="flex-1 flex items-center gap-2 text-sm text-gray-600">
              <Link href="/billing" className="hover:text-gray-900">
                Billing
              </Link>
              {pathname !== '/billing' && (
                <>
                  <span>/</span>
                  <span className="text-gray-900">
                    {navigation.find(item => isActive(item.href))?.name}
                  </span>
                </>
              )}
            </div>

            {/* Right Side Actions */}
            <div className="flex items-center gap-3">
              {/* Quick Stats */}
              {billingSummary && (
                <div className="hidden sm:flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-1">
                    <span className="text-gray-600">This Month:</span>
                    <span className="font-medium text-gray-900">
                      {formatCurrency(billingSummary.usageThisMonth.totalCost)}
                    </span>
                  </div>
                </div>
              )}

              {/* Notifications */}
              <Button variant="ghost" size="sm" className="relative">
                <BellIcon className="w-5 h-5" />
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full"></span>
              </Button>

              {/* User Avatar */}
              <Avatar className="h-8 w-8">
                <div className="w-full h-full bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-sm font-medium">U</span>
                </div>
              </Avatar>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
};

// Billing Header Component
export const BillingHeader: React.FC<{
  title: string;
  description?: string;
  actions?: React.ReactNode;
  breadcrumb?: Array<{ name: string; href?: string }>;
}> = ({ title, description, actions, breadcrumb }) => {
  return (
    <div className="mb-8">
      {/* Breadcrumb */}
      {breadcrumb && (
        <div className="flex items-center gap-2 text-sm text-gray-600 mb-4">
          <Link href="/billing" className="hover:text-gray-900">
            Billing
          </Link>
          {breadcrumb.map((item, index) => (
            <React.Fragment key={index}>
              <span>/</span>
              {item.href ? (
                <Link href={item.href} className="hover:text-gray-900">
                  {item.name}
                </Link>
              ) : (
                <span className="text-gray-900">{item.name}</span>
              )}
            </React.Fragment>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">{title}</h1>
          {description && (
            <p className="text-gray-600">{description}</p>
          )}
        </div>

        {actions && (
          <div className="flex items-center gap-3">{actions}</div>
        )}
      </div>
    </div>
  );
};

// Billing Alert Component
export const BillingAlert: React.FC<{
  type: 'success' | 'warning' | 'error' | 'info';
  title: string;
  message: string;
  actions?: React.ReactNode;
  dismissible?: boolean;
  onDismiss?: () => void;
}> = ({ type, title, message, actions, dismissible = false, onDismiss }) => {
  const alertStyles = {
    success: 'bg-green-50 border-green-200 text-green-800',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    error: 'bg-red-50 border-red-200 text-red-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800',
  };

  const iconStyles = {
    success: 'text-green-600',
    warning: 'text-yellow-600',
    error: 'text-red-600',
    info: 'text-blue-600',
  };

  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircleIcon className="w-5 h-5" />;
      case 'warning':
        return <ExclamationTriangleIcon className="w-5 h-5" />;
      case 'error':
        return <ExclamationTriangleIcon className="w-5 h-5" />;
      case 'info':
        return <BellIcon className="w-5 h-5" />;
    }
  };

  return (
    <div className={cn(
      'rounded-lg border p-4',
      alertStyles[type]
    )}>
      <div className="flex">
        <div className={cn('flex-shrink-0', iconStyles[type])}>
          {getIcon()}
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium">{title}</h3>
          <div className="mt-2 text-sm">{message}</div>
          {actions && (
            <div className="mt-4">{actions}</div>
          )}
        </div>
        {dismissible && onDismiss && (
          <div className="ml-auto pl-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={onDismiss}
              className={iconStyles[type]}
            >
              <XMarkIcon className="w-4 h-4" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

// Billing Stats Card Component
export const BillingStatsCard: React.FC<{
  title: string;
  value: string | number;
  change?: number;
  changeType?: 'increase' | 'decrease' | 'neutral';
  icon: React.ComponentType<any>;
  description?: string;
  trend?: 'up' | 'down' | 'stable';
}> = ({ title, value, change, changeType = 'neutral', icon: Icon, description, trend = 'stable' }) => {
  const getChangeColor = () => {
    if (changeType === 'increase') return 'text-green-600';
    if (changeType === 'decrease') return 'text-red-600';
    return 'text-gray-600';
  };

  const getTrendIcon = () => {
    if (trend === 'up') return '↗️';
    if (trend === 'down') return '↘️';
    return '→';
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {description && (
            <p className="text-sm text-gray-500 mt-1">{description}</p>
          )}
        </div>
        <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
          <Icon className="w-6 h-6 text-blue-600" />
        </div>
      </div>
      {change !== undefined && (
        <div className="flex items-center gap-2 mt-4">
          <span className={cn('text-sm font-medium', getChangeColor())}>
            {changeType === 'increase' && '+'}
            {change}%
          </span>
          <span className="text-sm">{getTrendIcon()}</span>
        </div>
      )}
    </div>
  );
};

export default BillingLayout;