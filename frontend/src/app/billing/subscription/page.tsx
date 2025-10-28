/**
 * 订阅管理页面
 *
 * 显示当前订阅、可选计划和升级/降级选项。
 */

'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';

// 组件导入
import { BillingLayout, BillingHeader, BillingAlert } from '@/components/billing/billing-layout';
import { PlanSelector } from '@/components/billing/plan-selector';
import { SubscriptionCard } from '@/components/billing/subscription-card';
import { UpgradeFlow } from '@/components/billing/upgrade-flow';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';

// Hooks导入
import { useSubscriptionManagement } from '@/store/billing-store';

// 图标导入
import {
  CreditCardIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  SparklesIcon,
  ArrowRightIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';

const SubscriptionManagement: React.FC = () => {
  const { currentSubscription, availablePlans, loading, error, actions } = useSubscriptionManagement();
  const [showUpgradeFlow, setShowUpgradeFlow] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        await Promise.all([
          actions.getCurrentSubscription(),
          actions.getAvailablePlans(),
        ]);
      } catch (error) {
        console.error('Failed to fetch subscription data:', error);
      }
    };

    fetchData();
  }, [actions]);

  const handlePlanSelect = async (planId: string) => {
    setSelectedPlan(planId);
    setShowUpgradeFlow(true);
  };

  const handleUpgradeComplete = async () => {
    setShowUpgradeFlow(false);
    setSelectedPlan(null);
    // 刷新订阅数据
    await actions.getCurrentSubscription();
  };

  const getPlanFeatures = (planType: string) => {
    const features = {
      free: [
        '1,000 API calls/month',
        'Basic models only',
        'Community support',
        'Rate limiting',
      ],
      pro: [
        '10,000 API calls/month',
        'All models available',
        'Priority support',
        'Higher rate limits',
        'Custom branding',
        'Advanced analytics',
      ],
      enterprise: [
        'Unlimited API calls',
        'All models + custom models',
        'Dedicated support',
        'No rate limits',
        'Custom integrations',
        'SLA guarantees',
        'Team collaboration',
        'Advanced security',
      ],
    };
    return features[planType as keyof typeof features] || [];
  };

  const getTrialStatus = () => {
    if (!currentSubscription || !currentSubscription.isTrial) return null;

    const daysRemaining = currentSubscription.daysInTrial;
    const totalTrialDays = 14; // 假设试用期为14天

    return {
      daysRemaining,
      totalTrialDays,
      progressPercentage: ((totalTrialDays - daysRemaining) / totalTrialDays) * 100,
    };
  };

  const trialStatus = getTrialStatus();

  if (loading) {
    return (
      <BillingLayout>
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-96 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </BillingLayout>
    );
  }

  return (
    <BillingLayout>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        {/* Page Header */}
        <BillingHeader
          title="Subscription Management"
          description="Manage your subscription plan, billing cycle, and payment methods"
          actions={
            currentSubscription && (
              <Button variant="outline" asChild>
                <Link href="/billing/payments/methods">
                  <CreditCardIcon className="w-4 h-4 mr-2" />
                  Manage Payment Methods
                </Link>
              </Button>
            )
          }
        />

        {/* Trial Alert */}
        {trialStatus && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mb-6"
          >
            <BillingAlert
              type="warning"
              title="Trial Period Active"
              description={`Your trial ends in ${trialStatus.daysRemaining} days. Upgrade now to continue using all features.`}
              actions={
                <div className="flex items-center gap-3">
                  <Button size="sm" onClick={() => setShowUpgradeFlow(true)}>
                    Upgrade Now
                  </Button>
                  <Button size="sm" variant="outline" asChild>
                    <Link href="/billing/usage">View Usage</Link>
                  </Button>
                </div>
              }
            />
          </motion.div>
        )}

        {/* Current Subscription */}
        {currentSubscription && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mb-8"
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CreditCardIcon className="w-5 h-5" />
                  Current Subscription
                </CardTitle>
                <CardDescription>
                  Your active subscription details and status
                </CardDescription>
              </CardHeader>
              <CardContent>
                <SubscriptionCard
                  subscription={currentSubscription}
                  onUpgrade={() => setShowUpgradeFlow(true)}
                  onManage={() => {/* TODO: Implement subscription management */}}
                />
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Available Plans */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <SparklesIcon className="w-5 h-5" />
                Available Plans
              </CardTitle>
              <CardDescription>
                Choose the plan that best fits your needs
              </CardDescription>
            </CardHeader>
            <CardContent>
              <PlanSelector
                plans={availablePlans || []}
                currentPlan={currentSubscription?.plan.type || 'free'}
                onSelectPlan={handlePlanSelect}
                loading={loading}
              />
            </CardContent>
          </Card>
        </motion.div>

        {/* Plan Features Comparison */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mt-8"
        >
          <Card>
            <CardHeader>
              <CardTitle>Plan Features</CardTitle>
              <CardDescription>
                Compare features across all available plans
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {['free', 'pro', 'enterprise'].map((planType, index) => (
                  <motion.div
                    key={planType}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 + index * 0.1 }}
                    className={`rounded-lg border-2 p-6 ${
                      planType === 'pro' ? 'border-blue-200 bg-blue-50' : 'border-gray-200'
                    }`}
                  >
                    {planType === 'pro' && (
                      <div className="flex items-center gap-2 mb-4">
                        <Badge className="bg-blue-600 text-white">Popular</Badge>
                        <span className="text-sm text-gray-600">Most chosen</span>
                      </div>
                    )}

                    <h3 className="text-xl font-bold mb-2 capitalize">{planType} Plan</h3>
                    <div className="text-2xl font-bold mb-6">
                      {planType === 'free' ? '$0' : planType === 'pro' ? '$29' : 'Custom'}
                      {planType !== 'free' && <span className="text-base font-normal text-gray-600">/month</span>}
                    </div>

                    <ul className="space-y-3">
                      {getPlanFeatures(planType).map((feature, featureIndex) => (
                        <li key={featureIndex} className="flex items-start gap-2">
                          <CheckCircleIcon className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                          <span className="text-sm text-gray-700">{feature}</span>
                        </li>
                      ))}
                    </ul>

                    <Button
                      className="w-full mt-6"
                      variant={currentSubscription?.plan.type === planType ? 'outline' : 'default'}
                      onClick={() => handlePlanSelect(planType)}
                      disabled={loading || currentSubscription?.plan.type === planType}
                    >
                      {currentSubscription?.plan.type === planType ? 'Current Plan' :
                       currentSubscription ? 'Switch Plan' : 'Get Started'}
                    </Button>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Billing FAQ */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="mt-8"
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <InformationCircleIcon className="w-5 h-5" />
                Billing FAQ
              </CardTitle>
              <CardDescription>
                Common questions about our billing and subscription
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {[
                  {
                    question: "Can I change my plan anytime?",
                    answer: "Yes, you can upgrade or downgrade your plan at any time. Changes will be prorated and take effect immediately."
                  },
                  {
                    question: "What happens if I exceed my quota?",
                    answer: "You'll receive notifications as you approach your limits. You can either wait for the next billing cycle or upgrade your plan."
                  },
                  {
                    question: "Do you offer refunds?",
                    answer: "We offer a 30-day money-back guarantee for all paid plans. Contact our support team for assistance."
                  },
                  {
                    question: "Can I cancel anytime?",
                    answer: "Yes, you can cancel your subscription at any time. You'll continue to have access until the end of your current billing period."
                  }
                ].map((faq, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.7 + index * 0.1 }}
                  >
                    <h4 className="font-medium text-gray-900 mb-2">{faq.question}</h4>
                    <p className="text-sm text-gray-600">{faq.answer}</p>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Upgrade Flow Dialog */}
      <AnimatePresence>
        {showUpgradeFlow && (
          <Dialog open={showUpgradeFlow} onOpenChange={setShowUpgradeFlow}>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>Change Subscription Plan</DialogTitle>
                <DialogDescription>
                  Select a new plan and billing cycle for your subscription
                </DialogDescription>
              </DialogHeader>

              <UpgradeFlow
                currentPlan={currentSubscription?.plan.type || 'free'}
                availablePlans={availablePlans || []}
                onComplete={handleUpgradeComplete}
                onCancel={() => setShowUpgradeFlow(false)}
              />
            </DialogContent>
          </Dialog>
        )}
      </AnimatePresence>
    </BillingLayout>
  );
};

export default SubscriptionManagement;