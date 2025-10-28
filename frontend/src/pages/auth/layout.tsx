/**
 * Authentication Layout Component
 * 提供认证页面的布局和样式
 */

import { ReactNode } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Link } from 'react-router-dom';
import { Logo } from '@/components/ui/logo';

interface AuthLayoutProps {
  children: ReactNode;
  title: string;
  description?: string;
  showBackLink?: boolean;
  backLinkText?: string;
  backLinkTo?: string;
}

export function AuthLayout({
  children,
  title,
  description,
  showBackLink = true,
  backLinkText = "返回首页",
  backLinkTo = "/"
}: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <Link to="/" className="inline-block">
            <Logo className="mx-auto h-12 w-auto" />
          </Link>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
            {title}
          </h2>
          {description && (
            <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
              {description}
            </p>
          )}
        </div>

        {/* Main Content */}
        <Card className="shadow-xl">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-bold text-center">
              {title}
            </CardTitle>
            {description && (
              <CardDescription className="text-center">
                {description}
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            {children}
          </CardContent>
        </Card>

        {/* Footer */}
        {showBackLink && (
          <div className="text-center">
            <Link
              to={backLinkTo}
              className="font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
            >
              {backLinkText}
            </Link>
          </div>
        )}

        {/* Additional Links */}
        <div className="text-center text-sm text-gray-600 dark:text-gray-400">
          <p>
            需要帮助？{' '}
            <Link
              to="/help"
              className="font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
            >
              联系支持
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}