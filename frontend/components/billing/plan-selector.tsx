/**
 * 计划选择器组件
 *
 * 显示可选的定价计划，允许用户选择和比较不同计划。
 */

'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';

// 类型导入
import { PricingPlan, PlanType, BillingCycle, PlanCardProps } from '@/types/billing';

// UI组件导入
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';

// 图标导入
import {
  CheckCircleIcon,
  SparklesIcon,
  RocketLaunchIcon,
  BuildingOfficeIcon,
  StarIcon,
} from '@heroicons/react/24/outline';

interface PlanSelectorProps {
  plans: PricingPlan[];
  currentPlan?: PlanType;
  onSelectPlan: (planId: string) => void;
  loading?: boolean;
}

interface PlanCard {
  plan: PricingPlan;
  isCurrent: boolean;
  isPopular: boolean;
  onSelect: () => void;
  loading?: boolean;
}

const PlanCard: React.FC<PlanCard> = ({ plan, isCurrent, isPopular, onSelect, loading }) => {
  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const getPlanIcon = (planType: PlanType) => {
    switch (planType) {
      case 'free':
        return <RocketLaunchIcon className="w-6 h-6" />;
      case 'pro':
        return <SparklesIcon className="w-6 h-6" />;
      case 'enterprise':
        return <BuildingOfficeIcon className="w-6 h-6" />;
      default:
        return <StarIcon className="w-6 h-6" />;
    }
  };

  const getPlanColor = (planType: PlanType) => {
    switch (planType) {
      case 'free':
        return 'from-gray-500 to-gray-600';
      case 'pro':
        return 'from-blue-500 to-purple-600';
      case 'enterprise':
        return 'from-green-500 to-teal-600';
      default:
        return 'from-blue-500 to-purple-600';
    }
  };

  const yearlyDiscount = plan.billingCycle === 'yearly' ? 0.2 : 0; // 20% discount for yearly

  return (
    <motion.div
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: 'spring', damping: 20, stiffness: 100 }}
    >
      <Card
        className={`relative h-full transition-all duration-200 hover:shadow-lg ${
          isPopular ? 'ring-2 ring-blue-500 ring-offset-2' : ''
        } ${isCurrent ? 'bg-blue-50 border-blue-200' : ''}`}
      >
        {isPopular && (
          <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
            <Badge className="bg-blue-600 text-white px-3 py-1">
              Most Popular
            </Badge>
          </div>
        )}

        {isCurrent && (
          <div className="absolute top-4 right-4">
            <Badge variant="secondary" className="bg-green-100 text-green-800">
              Current Plan
            </Badge>
          </div>
        )}

        <CardHeader className="text-center pb-4">
          <div className={`w-12 h-12 mx-auto mb-4 rounded-full bg-gradient-to-r ${getPlanColor(plan.type)} flex items-center justify-center text-white`}>
            {getPlanIcon(plan.type)}
          </div>

          <CardTitle className="text-xl capitalize">{plan.name}</CardTitle>
          <CardDescription className="text-sm">
            {plan.description}
          </CardDescription>

          <div className="mt-4">
            <div className="flex items-baseline justify-center gap-1">
              <span className="text-3xl font-bold">
                {formatCurrency(plan.price)}
              </span>
              <span className="text-gray-600">/{plan.billingCycle === 'monthly' ? 'month' : 'year'}</span>
            </div>

            {plan.billingCycle === 'yearly' && yearlyDiscount > 0 && (
              <div className="text-sm text-green-600 font-medium mt-1">
                Save {Math.round(yearlyDiscount * 100)}% with yearly billing
              </div>
            )}

            {plan.setupFee > 0 && (
              <div className="text-sm text-gray-600 mt-1">
                + {formatCurrency(plan.setupFee)} setup fee
              </div>
            )}
          </div>
        </CardHeader>

        <CardContent className="flex-1 flex flex-col">
          <div className="flex-1">
            <h4 className="font-medium mb-4 text-sm">What's included:</h4>
            <ul className="space-y-3">
              {plan.features.slice(0, 6).map((feature, index) => (
                <li key={index} className="flex items-start gap-2">
                  <CheckCircleIcon className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                  <span className="text-sm text-gray-700">{feature}</span>
                </li>
              ))}
            </ul>

            {plan.features.length > 6 && (
              <div className="text-sm text-gray-500 mt-2">
                +{plan.features.length - 6} more features
              </div>
            )}
          </div>

          <div className="mt-6 pt-4 border-t">
            <Button
              className="w-full"
              variant={isCurrent ? 'outline' : 'default'}
              onClick={onSelect}
              disabled={loading || isCurrent}
            >
              {loading ? (
                'Processing...'
              ) : isCurrent ? (
                'Current Plan'
              ) : plan.type === 'free' ? (
                'Get Started'
              ) : (
                `Upgrade to ${plan.name}`
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
};

export const PlanSelector: React.FC<PlanSelectorProps> = ({
  plans,
  currentPlan,
  onSelectPlan,
  loading = false,
}) => {
  const [billingCycle, setBillingCycle] = useState<BillingCycle>('monthly');
  const [selectedPlan, setSelectedPlan] = useState<string>('');

  // 过滤和分类计划
  const filteredPlans = plans.filter(plan => plan.billingCycle === billingCycle);
  const freePlans = filteredPlans.filter(plan => plan.type === 'free');
  const paidPlans = filteredPlans.filter(plan => plan.type !== 'free');

  // 确定最流行的计划
  const getPopularPlan = () => {
    const proPlan = paidPlans.find(plan => plan.type === 'pro');
    return proPlan || paidPlans.find(plan => plan.popular) || paidPlans[0];
  };

  const popularPlan = getPopularPlan();

  const handlePlanSelect = (planId: string) => {
    setSelectedPlan(planId);
    onSelectPlan(planId);
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        type: 'spring',
        damping: 20,
        stiffness: 100,
      },
    },
  };

  return (
    <div className="space-y-8">
      {/* Billing Cycle Toggle */}
      <div className="flex items-center justify-center">
        <div className="flex items-center gap-4 p-1 bg-gray-100 rounded-lg">
          <div className="flex items-center gap-2">
            <Label
              htmlFor="monthly"
              className={`cursor-pointer px-3 py-1 rounded-md transition-colors ${
                billingCycle === 'monthly' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600'
              }`}
            >
              Monthly
            </Label>
            <RadioGroup
              value={billingCycle}
              onValueChange={(value) => setBillingCycle(value as BillingCycle)}
              className="flex"
            >
              <RadioGroupItem value="monthly" id="monthly" className="sr-only" />
            </RadioGroup>
          </div>

          <div className="flex items-center gap-2">
            <Label
              htmlFor="yearly"
              className={`cursor-pointer px-3 py-1 rounded-md transition-colors ${
                billingCycle === 'yearly' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600'
              }`}
            >
              Yearly
            </Label>
            <Badge variant="secondary" className="text-xs">
              Save 20%
            </Badge>
            <RadioGroup
              value={billingCycle}
              onValueChange={(value) => setBillingCycle(value as BillingCycle)}
              className="flex"
            >
              <RadioGroupItem value="yearly" id="yearly" className="sr-only" />
            </RadioGroup>
          </div>
        </div>
      </div>

      {/* Free Plans */}
      {freePlans.length > 0 && (
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <h3 className="text-lg font-semibold mb-4 text-center">Free Plan</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {freePlans.map((plan) => (
              <motion.div key={plan.id} variants={itemVariants}>
                <PlanCard
                  plan={plan}
                  isCurrent={currentPlan === plan.type}
                  isPopular={plan.popular}
                  onSelect={() => handlePlanSelect(plan.id)}
                  loading={loading && selectedPlan === plan.id}
                />
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Paid Plans */}
      {paidPlans.length > 0 && (
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          transition={{ delay: 0.2 }}
        >
          <h3 className="text-lg font-semibold mb-4 text-center">Premium Plans</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {paidPlans.map((plan) => (
              <motion.div key={plan.id} variants={itemVariants}>
                <PlanCard
                  plan={plan}
                  isCurrent={currentPlan === plan.type}
                  isPopular={plan.id === popularPlan?.id}
                  onSelect={() => handlePlanSelect(plan.id)}
                  loading={loading && selectedPlan === plan.id}
                />
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Additional Information */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
        className="text-center space-y-4"
      >
        <div className="text-sm text-gray-600">
          <p>• All plans include 24/7 email support</p>
          <p>• Cancel or change your plan anytime</p>
          <p>• 30-day money-back guarantee for paid plans</p>
        </div>

        <div className="flex items-center justify-center gap-4">
          <Button variant="outline" size="sm">
            Compare All Features
          </Button>
          <Button variant="outline" size="sm">
            Contact Sales
          </Button>
        </div>
      </motion.div>
    </div>
  );
};

export default PlanSelector;