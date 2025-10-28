/**
 * 订阅卡片组件
 *
 * 用于显示用户当前订阅信息，包括状态、到期时间、管理操作等。
 */

'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  CreditCardIcon,
  ArrowPathIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  XMarkIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolidIcon } from '@heroicons/react/24/solid';

import { Subscription, SubscriptionStatus, PlanType } from '@/types/billing';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';

interface SubscriptionCardProps {
  subscription: Subscription;
  onCancel?: () => void;
  onUpgrade?: () => void;
  onManage?: () => void;
  onRenew?: () => void;
  loading?: boolean;
  className?: string;
}

const subscriptionStatusConfig = {
  [SubscriptionStatus.ACTIVE]: {
    label: 'Active',
    color: 'green',
    bgColor: 'bg-green-50',
    textColor: 'text-green-700',
    borderColor: 'border-green-200',
    icon: CheckCircleSolidIcon,
  },
  [SubscriptionStatus.TRIAL]: {
    label: 'Trial',
    color: 'blue',
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-200',
    icon: ClockIcon,
  },
  [SubscriptionStatus.PAST_DUE]: {
    label: 'Past Due',
    color: 'yellow',
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-700',
    borderColor: 'border-yellow-200',
    icon: ExclamationTriangleIcon,
  },
  [SubscriptionStatus.CANCELLED]: {
    label: 'Cancelled',
    color: 'red',
    bgColor: 'bg-red-50',
    textColor: 'text-red-700',
    borderColor: 'border-red-200',
    icon: XMarkIcon,
  },
  [SubscriptionStatus.EXPIRED]: {
    label: 'Expired',
    color: 'gray',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-700',
    borderColor: 'border-gray-200',
    icon: XMarkIcon,
  },
  [SubscriptionStatus.UNPAID]: {
    label: 'Unpaid',
    color: 'red',
    bgColor: 'bg-red-50',
    textColor: 'text-red-700',
    borderColor: 'border-red-200',
    icon: ExclamationTriangleIcon,
  },
};

const planTypeConfig = {
  [PlanType.FREE]: {
    name: 'Free Plan',
    description: 'Basic features for getting started',
    color: 'gray',
    gradient: 'from-gray-500 to-gray-600',
  },
  [PlanType.PRO]: {
    name: 'Pro Plan',
    description: 'Professional features for developers',
    color: 'blue',
    gradient: 'from-blue-500 to-blue-600',
  },
  [PlanType.ENTERPRISE]: {
    name: 'Enterprise Plan',
    description: 'Advanced features for organizations',
    color: 'purple',
    gradient: 'from-purple-500 to-purple-600',
  },
};

export const SubscriptionCard: React.FC<SubscriptionCardProps> = ({
  subscription,
  onCancel,
  onUpgrade,
  onManage,
  onRenew,
  loading = false,
  className,
}) => {
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [showManageDialog, setShowManageDialog] = useState(false);

  const statusConfig = subscriptionStatusConfig[subscription.status];
  const planConfig = planTypeConfig[subscription.plan.type as PlanType] || planTypeConfig[PlanType.FREE];
  const StatusIcon = statusConfig.icon;

  const isTrialing = subscription.isTrial;
  const willCancelAtPeriodEnd = subscription.cancelAtPeriodEnd;
  const isExpired = subscription.isExpired;

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getRemainingDays = () => {
    if (subscription.status === SubscriptionStatus.CANCELLED || isExpired) {
      return 0;
    }
    return Math.max(0, subscription.daysUntilRenewal);
  };

  const getTrialRemainingDays = () => {
    if (!isTrialing || !subscription.trialEnd) {
      return 0;
    }
    const trialEnd = new Date(subscription.trialEnd);
    const now = new Date();
    const diffTime = trialEnd.getTime() - now.getTime();
    return Math.max(0, Math.ceil(diffTime / (1000 * 60 * 60 * 24)));
  };

  const handleCancel = async () => {
    setShowCancelDialog(false);
    if (onCancel) {
      onCancel();
    }
  };

  const handleManage = () => {
    setShowManageDialog(false);
    if (onManage) {
      onManage();
    }
  };

  return (
    <Card className={cn(
      'relative overflow-hidden',
      statusConfig.borderColor,
      'border-2',
      className
    )}>
      {/* Status Badge */}
      <div className="absolute top-4 right-4">
        <Badge className={cn(
          'flex items-center gap-1 px-3 py-1',
          statusConfig.bgColor,
          statusConfig.textColor,
          'border-0'
        )}>
          <StatusIcon className="w-4 h-4" />
          {statusConfig.label}
        </Badge>
      </div>

      {/* Plan Header */}
      <div className="p-6 pb-4">
        <div className="flex items-center gap-4 mb-4">
          <div className={cn(
            'w-12 h-12 rounded-lg bg-gradient-to-r flex items-center justify-center',
            planConfig.gradient
          )}>
            <CreditCardIcon className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-xl font-semibold text-gray-900">
              {planConfig.name}
            </h3>
            <p className="text-sm text-gray-600">
              {planConfig.description}
            </p>
          </div>
        </div>

        {/* Pricing Info */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Monthly Price</span>
            <span className="font-medium text-gray-900">
              {formatCurrency(subscription.unitPrice)}
            </span>
          </div>

          {subscription.quantity > 1 && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Quantity</span>
              <span className="font-medium text-gray-900">{subscription.quantity}</span>
            </div>
          )}

          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Billing Cycle</span>
            <span className="font-medium text-gray-900 capitalize">
              {subscription.billingCycle}
            </span>
          </div>
        </div>
      </div>

      {/* Status-specific Information */}
      <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
        {isTrialing && (
          <div className="flex items-center gap-2 text-blue-700">
            <ClockIcon className="w-4 h-4" />
            <span className="text-sm">
              Trial ends in {getTrialRemainingDays()} days ({formatDate(subscription.trialEnd!)})
            </span>
          </div>
        )}

        {subscription.status === SubscriptionStatus.ACTIVE && !isTrialing && (
          <div className="flex items-center gap-2 text-green-700">
            <CheckCircleSolidIcon className="w-4 h-4" />
            <span className="text-sm">
              {getRemainingDays()} days remaining until {formatDate(subscription.currentPeriodEnd)}
            </span>
          </div>
        )}

        {willCancelAtPeriodEnd && subscription.status === SubscriptionStatus.ACTIVE && (
          <div className="flex items-center gap-2 text-orange-700">
            <InformationCircleIcon className="w-4 h-4" />
            <span className="text-sm">
              Will cancel on {formatDate(subscription.currentPeriodEnd)}
            </span>
          </div>
        )}

        {subscription.status === SubscriptionStatus.PAST_DUE && (
          <div className="flex items-center gap-2 text-yellow-700">
            <ExclamationTriangleIcon className="w-4 h-4" />
            <span className="text-sm">
              Payment overdue. Please update your payment method.
            </span>
          </div>
        )}

        {isExpired && (
          <div className="flex items-center gap-2 text-red-700">
            <XMarkIcon className="w-4 h-4" />
            <span className="text-sm">
              Subscription expired on {formatDate(subscription.currentPeriodEnd)}
            </span>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="p-6 pt-4">
        <div className="flex flex-wrap gap-2">
          {subscription.status === SubscriptionStatus.ACTIVE && !isTrialing && (
            <>
              {onUpgrade && subscription.plan.type !== PlanType.ENTERPRISE && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onUpgrade}
                  disabled={loading}
                  className="flex items-center gap-2"
                >
                  <ArrowUpIcon className="w-4 h-4" />
                  Upgrade
                </Button>
              )}

              {onManage && (
                <Dialog open={showManageDialog} onOpenChange={setShowManageDialog}>
                  <DialogTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={loading}
                      className="flex items-center gap-2"
                    >
                      <CreditCardIcon className="w-4 h-4" />
                      Manage
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Manage Subscription</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                      <p className="text-gray-600">
                        Choose an action to manage your subscription:
                      </p>
                      <div className="space-y-2">
                        <Button
                          variant="outline"
                          className="w-full justify-start"
                          onClick={handleManage}
                        >
                          <CreditCardIcon className="w-4 h-4 mr-2" />
                          Update Payment Method
                        </Button>
                        <Button
                          variant="outline"
                          className="w-full justify-start"
                          onClick={() => setShowManageDialog(false)}
                        >
                          <InformationCircleIcon className="w-4 h-4 mr-2" />
                          View Usage Statistics
                        </Button>
                        <Button
                          variant="outline"
                          className="w-full justify-start"
                          onClick={() => setShowManageDialog(false)}
                        >
                          <ArrowPathIcon className="w-4 h-4 mr-2" />
                          Change Billing Cycle
                        </Button>
                      </div>
                    </div>
                  </DialogContent>
                </Dialog>
              )}

              {onCancel && !willCancelAtPeriodEnd && (
                <Dialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
                  <DialogTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={loading}
                      className="flex items-center gap-2 text-red-600 hover:text-red-700"
                    >
                      <XMarkIcon className="w-4 h-4" />
                      Cancel
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Cancel Subscription</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                      <p className="text-gray-600">
                        Are you sure you want to cancel your subscription? You'll continue to have access
                        until the end of your current billing period.
                      </p>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          onClick={() => setShowCancelDialog(false)}
                          className="flex-1"
                        >
                          Keep Subscription
                        </Button>
                        <Button
                          variant="destructive"
                          onClick={handleCancel}
                          disabled={loading}
                          className="flex-1"
                        >
                          Cancel Subscription
                        </Button>
                      </div>
                    </div>
                  </DialogContent>
                </Dialog>
              )}
            </>
          )}

          {isTrialing && onUpgrade && (
            <Button
              size="sm"
              onClick={onUpgrade}
              disabled={loading}
              className="flex items-center gap-2"
            >
              <ArrowUpIcon className="w-4 h-4" />
              Upgrade Now
            </Button>
          )}

          {isExpired && onRenew && (
            <Button
              size="sm"
              onClick={onRenew}
              disabled={loading}
              className="flex items-center gap-2"
            >
              <ArrowPathIcon className="w-4 h-4" />
              Renew Subscription
            </Button>
          )}

          {subscription.status === SubscriptionStatus.PAST_DUE && (
            <Button
              size="sm"
              onClick={onManage}
              disabled={loading}
              className="flex items-center gap-2"
            >
              <CreditCardIcon className="w-4 h-4" />
              Update Payment
            </Button>
          )}
        </div>
      </div>

      {/* Loading Overlay */}
      {loading && (
        <motion.div
          className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </motion.div>
      )}
    </Card>
  );
};

// Subscription Summary Component
interface SubscriptionSummaryProps {
  subscription: Subscription;
  className?: string;
}

export const SubscriptionSummary: React.FC<SubscriptionSummaryProps> = ({
  subscription,
  className,
}) => {
  const planConfig = planTypeConfig[subscription.plan.type as PlanType] || planTypeConfig[PlanType.FREE];
  const statusConfig = subscriptionStatusConfig[subscription.status];
  const StatusIcon = statusConfig.icon;

  return (
    <div className={cn('flex items-center gap-4', className)}>
      <div className={cn(
        'w-10 h-10 rounded-lg bg-gradient-to-r flex items-center justify-center',
        planConfig.gradient
      )}>
        <CreditCardIcon className="w-5 h-5 text-white" />
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <h4 className="font-medium text-gray-900">{planConfig.name}</h4>
          <Badge className={cn(
            'flex items-center gap-1 text-xs',
            statusConfig.bgColor,
            statusConfig.textColor,
            'border-0'
          )}>
            <StatusIcon className="w-3 h-3" />
            {statusConfig.label}
          </Badge>
        </div>
        <p className="text-sm text-gray-600">
          ${subscription.unitPrice.toFixed(2)}/{subscription.billingCycle}
        </p>
      </div>
    </div>
  );
};

export default SubscriptionCard;