/**
 * 配额指��器组件
 *
 * 显示特定配额的使用情况和状态。
 */

'use client';

import React from 'react';
import { motion } from 'framer-motion';

// 类型导入
import { QuotaIndicatorProps } from '@/types/billing';

// UI组件导入
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

// 图标导入
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  BoltIcon,
  ServerIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';

const QuotaIndicator: React.FC<QuotaIndicatorProps> = ({
  quota,
  showDetails = false,
}) => {
  const getIcon = (type: string) => {
    switch (type) {
      case 'API_CALLS':
        return <BoltIcon className="w-5 h-5" />;
      case 'TOKENS':
        return <DocumentTextIcon className="w-5 h-5" />;
      case 'STORAGE':
        return <ServerIcon className="w-5 h-5" />;
      case 'REQUESTS_PER_MINUTE':
        return <ClockIcon className="w-5 h-5" />;
      default:
        return <ExclamationTriangleIcon className="w-5 h-5" />;
    }
  };

  const getStatusColor = (percentage: number) => {
    if (percentage >= 90) return 'text-red-600 bg-red-50 border-red-200';
    if (percentage >= 70) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-green-600 bg-green-50 border-green-200';
  };

  const getProgressColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getStatusIcon = (percentage: number) => {
    if (percentage >= 90) return <ExclamationTriangleIcon className="w-4 h-4" />;
    if (percentage >= 70) return <ExclamationTriangleIcon className="w-4 h-4" />;
    return <CheckCircleIcon className="w-4 h-4" />;
  };

  const formatRemaining = (remaining: number, type: string) => {
    if (type === 'STORAGE') {
      return remaining > 1024 ? `${(remaining / 1024).toFixed(1)}GB` : `${remaining}MB`;
    }
    return remaining.toLocaleString();
  };

  const getStatusText = (percentage: number) => {
    if (percentage >= 90) return 'Critical';
    if (percentage >= 70) return 'Warning';
    return 'Healthy';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-3"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`p-2 rounded-lg ${getStatusColor(quota.percentageUsed)}`}>
            {getIcon(quota.type)}
          </div>
          <div>
            <h4 className="font-medium text-gray-900 capitalize">
              {quota.type.replace('_', ' ').toLowerCase()}
            </h4>
            <p className="text-sm text-gray-600">{quota.message}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge
            variant="secondary"
            className={`${getStatusColor(quota.percentageUsed)} border`}
          >
            {getStatusIcon(quota.percentageUsed)}
            <span className="ml-1">{getStatusText(quota.percentageUsed)}</span>
          </Badge>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Used</span>
          <span className="font-medium">
            {quota.percentageUsed.toFixed(1)}%
          </span>
        </div>
        <Progress
          value={quota.percentageUsed}
          className="h-2"
          // Add custom color using inline styles since Progress component might not support dynamic colors
          style={{
            ['--progress-background' as string]: getProgressColor(quota.percentageUsed),
          }}
        />
      </div>

      {/* Details */}
      {showDetails && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          transition={{ duration: 0.2 }}
          className="pt-2 border-t space-y-2"
        >
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Current Usage</span>
              <div className="font-medium">{quota.currentUsage.toLocaleString()}</div>
            </div>
            <div>
              <span className="text-gray-600">Limit</span>
              <div className="font-medium">{quota.limit.toLocaleString()}</div>
            </div>
            <div>
              <span className="text-gray-600">Remaining</span>
              <div className="font-medium text-green-600">
                {formatRemaining(quota.limit - quota.currentUsage, quota.type)}
              </div>
            </div>
            <div>
              <span className="text-gray-600">Percentage Used</span>
              <div className="font-medium">{quota.percentageUsed.toFixed(1)}%</div>
            </div>
          </div>

          {/* Alert for critical usage */}
          {quota.percentageUsed >= 90 && (
            <Alert className="bg-red-50 border-red-200">
              <ExclamationTriangleIcon className="w-4 h-4 text-red-600" />
              <AlertDescription className="text-red-800">
                You're about to reach your {quota.type.replace('_', ' ').toLowerCase()} limit.
                Consider upgrading your plan to avoid service interruption.
              </AlertDescription>
            </Alert>
          )}

          {/* Warning for approaching limits */}
          {quota.percentageUsed >= 70 && quota.percentageUsed < 90 && (
            <Alert className="bg-yellow-50 border-yellow-200">
              <ExclamationTriangleIcon className="w-4 h-4 text-yellow-600" />
              <AlertDescription className="text-yellow-800">
                You're approaching your {quota.type.replace('_', ' ').toLowerCase()} limit.
                Monitor your usage or consider upgrading your plan.
              </AlertDescription>
            </Alert>
          )}
        </motion.div>
      )}
    </motion.div>
  );
};

export default QuotaIndicator;