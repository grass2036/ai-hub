/**
 * 价格���划卡片组件
 *
 * 用于展示不同的订阅计划，支持计划选择和对比功能。
 */

'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { CheckIcon, StarIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { CheckCircleIcon } from '@heroicons/react/24/solid';

import { PricingPlan, PlanType, BillingCycle } from '@/types/billing';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface PricingPlanCardProps {
  plan: PricingPlan;
  currentPlan?: PlanType;
  billingCycle: BillingCycle;
  onSelectPlan: (plan: PricingPlan) => void;
  loading?: boolean;
  disabled?: boolean;
  className?: string;
}

const planTypeConfig = {
  [PlanType.FREE]: {
    name: 'Free',
    description: 'Perfect for getting started',
    color: 'gray',
    gradient: 'from-gray-500 to-gray-600',
    borderColor: 'border-gray-200',
    hoverBorderColor: 'hover:border-gray-300',
  },
  [PlanType.PRO]: {
    name: 'Pro',
    description: 'For professional developers',
    color: 'blue',
    gradient: 'from-blue-500 to-blue-600',
    borderColor: 'border-blue-200',
    hoverBorderColor: 'hover:border-blue-300',
  },
  [PlanType.ENTERPRISE]: {
    name: 'Enterprise',
    description: 'For large organizations',
    color: 'purple',
    gradient: 'from-purple-500 to-purple-600',
    borderColor: 'border-purple-200',
    hoverBorderColor: 'hover:border-purple-300',
  },
};

const BillingCycleToggle = ({
  value,
  onChange,
  disabled = false,
}: {
  value: BillingCycle;
  onChange: (cycle: BillingCycle) => void;
  disabled?: boolean;
}) => {
  return (
    <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
      <button
        className={cn(
          'flex-1 py-2 px-3 text-sm font-medium rounded-md transition-all',
          value === BillingCycle.MONTHLY
            ? 'bg-white text-gray-900 shadow-sm'
            : 'text-gray-600 hover:text-gray-900'
        )}
        onClick={() => onChange(BillingCycle.MONTHLY)}
        disabled={disabled}
      >
        Monthly
      </button>
      <button
        className={cn(
          'flex-1 py-2 px-3 text-sm font-medium rounded-md transition-all',
          value === BillingCycle.YEARLY
            ? 'bg-white text-gray-900 shadow-sm'
            : 'text-gray-600 hover:text-gray-900'
        )}
        onClick={() => onChange(BillingCycle.YEARLY)}
        disabled={disabled}
      >
        Yearly
        <Badge variant="secondary" className="ml-1 text-xs">
          Save 20%
        </Badge>
      </button>
    </div>
  );
};

export const PricingPlanCard: React.FC<PricingPlanCardProps> = ({
  plan,
  currentPlan,
  billingCycle,
  onSelectPlan,
  loading = false,
  disabled = false,
  className,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const config = planTypeConfig[plan.type];

  const isCurrentPlan = currentPlan === plan.type;
  const isUpgrade = currentPlan && plan.type !== currentPlan;

  // 计算价格
  const monthlyPrice = billingCycle === BillingCycle.YEARLY
    ? plan.price * 12 * 0.8 // 年付8折
    : plan.price;

  const savings = billingCycle === BillingCycle.YEARLY ? 20 : 0;

  const handleSelectPlan = () => {
    if (!disabled && !loading) {
      onSelectPlan(plan);
    }
  };

  return (
    <motion.div
      className={cn(
        'relative bg-white rounded-2xl border-2 p-8 transition-all duration-200',
        config.borderColor,
        config.hoverBorderColor,
        plan.popular && 'ring-2 ring-blue-500 ring-offset-2',
        isCurrentPlan && 'bg-gray-50',
        disabled && 'opacity-50 cursor-not-allowed',
        !disabled && !isCurrentPlan && 'hover:shadow-lg hover:scale-105 cursor-pointer',
        className
      )}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      whileHover={!disabled && !isCurrentPlan ? { scale: 1.02 } : {}}
      transition={{ duration: 0.2 }}
    >
      {/* Popular Badge */}
      {plan.popular && (
        <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
          <Badge className={cn(
            'px-4 py-1 text-sm font-medium bg-gradient-to-r',
            config.gradient,
            'text-white border-0'
          )}>
            <StarIcon className="w-4 h-4 mr-1" />
            Most Popular
          </Badge>
        </div>
      )}

      {/* Current Plan Badge */}
      {isCurrentPlan && (
        <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
          <Badge className="px-4 py-1 text-sm font-medium bg-green-500 text-white border-0">
            <CheckCircleIcon className="w-4 h-4 mr-1" />
            Current Plan
          </Badge>
        </div>
      )}

      <div className="text-center">
        {/* Plan Name */}
        <h3 className="text-2xl font-bold text-gray-900 mb-2">
          {plan.name}
        </h3>

        {/* Plan Description */}
        <p className="text-gray-600 mb-6">
          {plan.description}
        </p>

        {/* Price */}
        <div className="mb-6">
          <div className="flex items-baseline justify-center">
            <span className="text-5xl font-bold text-gray-900">
              ${monthlyPrice.toFixed(2)}
            </span>
            <span className="text-gray-600 ml-2">
              /{billingCycle === BillingCycle.MONTHLY ? 'month' : 'month (billed yearly)'}
            </span>
          </div>

          {savings > 0 && (
            <div className="mt-2 text-sm text-green-600 font-medium">
              Save ${((plan.price * 12 - monthlyPrice * 12)).toFixed(2)} per year
            </div>
          )}
        </div>

        {/* Trial Info */}
        {plan.trialDays > 0 && (
          <div className="mb-6">
            <Badge variant="outline" className="text-blue-600 border-blue-200">
              <SparklesIcon className="w-4 h-4 mr-1" />
              {plan.trialDays} days free trial
            </Badge>
          </div>
        )}

        {/* Features */}
        <div className="space-y-3 mb-8 text-left">
          {plan.features.map((feature, index) => (
            <div key={index} className="flex items-start">
              <CheckIcon className="w-5 h-5 text-green-500 mr-3 mt-0.5 flex-shrink-0" />
              <span className="text-gray-700">{feature}</span>
            </div>
          ))}
        </div>

        {/* CTA Button */}
        <Button
          className={cn(
            'w-full py-3 text-base font-medium transition-all',
            plan.popular && config.gradient.replace('from-', 'bg-gradient-to-r '),
            !plan.popular && (isCurrentPlan
              ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              : 'bg-gray-900 text-white hover:bg-gray-800'
            ),
            loading && 'opacity-50 cursor-not-allowed'
          )}
          onClick={handleSelectPlan}
          disabled={disabled || loading || isCurrentPlan}
        >
          {loading ? (
            <div className="flex items-center justify-center">
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
              Processing...
            </div>
          ) : isCurrentPlan ? (
            'Current Plan'
          ) : isUpgrade ? (
            'Upgrade Plan'
          ) : plan.type === PlanType.FREE ? (
            'Get Started'
          ) : (
            'Choose Plan'
          )}
        </Button>

        {/* Setup Fee */}
        {plan.setupFee > 0 && (
          <div className="mt-4 text-sm text-gray-600">
            One-time setup fee: ${plan.setupFee.toFixed(2)}
          </div>
        )}
      </div>

      {/* Hover Effect Overlay */}
      {!disabled && !isCurrentPlan && isHovered && (
        <motion.div
          className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-purple-500/5 rounded-2xl pointer-events-none"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2 }}
        />
      )}
    </motion.div>
  );
};

// Pricing Plans Container
interface PricingPlansProps {
  plans: PricingPlan[];
  currentPlan?: PlanType;
  onSelectPlan: (plan: PricingPlan) => void;
  loading?: boolean;
  className?: string;
}

export const PricingPlans: React.FC<PricingPlansProps> = ({
  plans,
  currentPlan,
  onSelectPlan,
  loading = false,
  className,
}) => {
  const [billingCycle, setBillingCycle] = useState<BillingCycle>(BillingCycle.MONTHLY);

  // Filter plans by billing cycle
  const filteredPlans = plans.filter(plan => plan.billingCycle === billingCycle);

  return (
    <div className={cn('w-full max-w-7xl mx-auto', className)}>
      {/* Billing Cycle Toggle */}
      <div className="flex justify-center mb-12">
        <BillingCycleToggle
          value={billingCycle}
          onChange={setBillingCycle}
          disabled={loading}
        />
      </div>

      {/* Plans Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {filteredPlans.map((plan) => (
          <PricingPlanCard
            key={plan.id}
            plan={plan}
            currentPlan={currentPlan}
            billingCycle={billingCycle}
            onSelectPlan={onSelectPlan}
            loading={loading}
          />
        ))}
      </div>

      {/* Additional Info */}
      <div className="mt-12 text-center text-gray-600">
        <p className="mb-2">
          All plans include core features such as API access, basic analytics, and email support.
        </p>
        <p>
          Need a custom plan?{' '}
          <a href="/contact" className="text-blue-600 hover:text-blue-700 font-medium">
            Contact our sales team
          </a>
        </p>
      </div>
    </div>
  );
};

// Plan Comparison Table
interface PlanComparisonProps {
  plans: PricingPlan[];
  className?: string;
}

export const PlanComparison: React.FC<PlanComparisonProps> = ({
  plans,
  className,
}) => {
  // Get all unique features from all plans
  const allFeatures = Array.from(
    new Set(plans.flatMap(plan => plan.features))
  ).sort();

  return (
    <div className={cn('w-full max-w-6xl mx-auto overflow-x-auto', className)}>
      <table className="w-full bg-white rounded-lg overflow-hidden">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-4 text-left text-sm font-medium text-gray-900">
              Features
            </th>
            {plans.map((plan) => {
              const config = planTypeConfig[plan.type];
              return (
                <th key={plan.id} className="px-6 py-4 text-center text-sm font-medium text-gray-900">
                  <div className="flex flex-col items-center">
                    <span className={cn(
                      'px-3 py-1 rounded-full text-white text-xs font-medium mb-1',
                      config.gradient.replace('from-', 'bg-gradient-to-r ')
                    )}>
                      {plan.name}
                    </span>
                    <span className="text-gray-600">
                      ${plan.price.toFixed(2)}/mo
                    </span>
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {allFeatures.map((feature, index) => (
            <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
              <td className="px-6 py-4 text-sm text-gray-900">
                {feature}
              </td>
              {plans.map((plan) => (
                <td key={plan.id} className="px-6 py-4 text-center">
                  {plan.features.includes(feature) ? (
                    <CheckIcon className="w-5 h-5 text-green-500 mx-auto" />
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default PricingPlanCard;