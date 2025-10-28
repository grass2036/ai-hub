/**
 * 订阅管理页面
 *
 * 提供订阅计划选择、升级、取消等功能。
 */

'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CreditCardIcon,
  ArrowPathIcon,
  InformationCircleIcon,
  SparklesIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

import { BillingLayout, BillingHeader } from '@/components/billing/billing-layout';
import { SubscriptionCard } from '@/components/billing/subscription-card';
import { PricingPlans } from '@/components/billing/pricing-plan-card';
import { UpgradeSubscriptionFlow } from '@/components/billing/upgrade-subscription-flow';
import { useSubscriptionManagement } from '@/store/billing-store';
import { PlanType } from '@/types/billing';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function SubscriptionPage() {
  const {
    currentSubscription,
    availablePlans,
    loading,
    error,
    actions,
  } = useSubscriptionManagement();

  const [showUpgradeFlow, setShowUpgradeFlow] = useState(false);
  const [showPlans, setShowPlans] = useState(false);

  useEffect(() => {
    actions.getCurrentSubscription();
    actions.getAvailablePlans();
  }, [actions]);

  const handleUpgradeComplete = (newSubscription: any) => {
    setShowUpgradeFlow(false);
    actions.getCurrentSubscription(); // Refresh subscription data
  };

  const handleManageSubscription = () => {
    // Implement management functionality (change payment method, update billing info, etc.)
    console.log('Manage subscription');
  };

  const handleCancelSubscription = () => {
    if (currentSubscription) {
      actions.cancelSubscription(currentSubscription.id, false);
    }
  };

  const handleSelectPlan = (plan: any) => {
    // Handle plan selection for new subscriptions or upgrades
    console.log('Selected plan:', plan);
  };

  if (loading) {
    return (
      <BillingLayout>
        <div className="space-y-6">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-64 mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-96"></div>
          </div>
          <Card className="p-6">
            <div className="animate-pulse">
              <div className="h-32 bg-gray-200 rounded"></div>
            </div>
          </Card>
        </div>
      </BillingLayout>
    );
  }

  return (
    <BillingLayout>
      <div className="space-y-6">
        <BillingHeader
          title="Subscription Management"
          description="Manage your subscription plan, billing details, and payment methods"
          actions={
            !currentSubscription && (
              <Button onClick={() => setShowPlans(true)}>
                <CreditCardIcon className="w-4 h-4 mr-2" />
                Choose Plan
              </Button>
            )
          }
          breadcrumb={[
            { name: 'Billing', href: '/billing' },
            { name: 'Subscription' },
          ]}
        />

        {/* Current Subscription */}
        {currentSubscription ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <SubscriptionCard
              subscription={currentSubscription}
              onUpgrade={() => setShowUpgradeFlow(true)}
              onManage={handleManageSubscription}
              onCancel={handleCancelSubscription}
            />
          </motion.div>
        ) : (
          <Card className="p-12 text-center">
            <CreditCardIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              No Active Subscription
            </h3>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              You don't have an active subscription. Choose a plan to start using our premium features.
            </p>
            <Button onClick={() => setShowPlans(true)} size="lg">
              <SparklesIcon className="w-5 h-5 mr-2" />
              Choose a Plan
            </Button>
          </Card>
        )}

        {/* Upgrade Flow Modal */}
        <AnimatePresence>
          {showUpgradeFlow && currentSubscription && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
              onClick={() => setShowUpgradeFlow(false)}
            >
              <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="w-full max-w-4xl max-h-[90vh] overflow-y-auto mx-4"
              >
                <UpgradeSubscriptionFlow
                  currentSubscription={currentSubscription}
                  availablePlans={availablePlans}
                  onComplete={handleUpgradeComplete}
                  onCancel={() => setShowUpgradeFlow(false)}
                />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Plans Selection Modal */}
        <AnimatePresence>
          {showPlans && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
              onClick={() => setShowPlans(false)}
            >
              <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="w-full max-w-6xl max-h-[90vh] overflow-y-auto mx-4"
              >
                <div className="bg-white rounded-2xl p-8">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h2 className="text-2xl font-bold text-gray-900 mb-2">
                        Choose Your Plan
                      </h2>
                      <p className="text-gray-600">
                        Select the plan that best fits your needs
                      </p>
                    </div>
                    <Button variant="ghost" onClick={() => setShowPlans(false)}>
                      ×
                    </Button>
                  </div>

                  <PricingPlans
                    plans={availablePlans}
                    onSelectPlan={handleSelectPlan}
                    loading={loading}
                  />
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Subscription Benefits */}
        {currentSubscription && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Billing History */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Billing Information
              </h3>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Current Plan</span>
                  <span className="font-medium text-gray-900">
                    {currentSubscription.plan.type.charAt(0).toUpperCase() +
                      currentSubscription.plan.type.slice(1)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Billing Cycle</span>
                  <span className="font-medium text-gray-900 capitalize">
                    {currentSubscription.billingCycle}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Monthly Cost</span>
                  <span className="font-medium text-gray-900">
                    ${currentSubscription.unitPrice.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Next Billing Date</span>
                  <span className="font-medium text-gray-900">
                    {new Date(currentSubscription.currentPeriodEnd).toLocaleDateString()}
                  </span>
                </div>
                {currentSubscription.cancelAtPeriodEnd && (
                  <div className="flex items-center gap-2 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                    <InformationCircleIcon className="w-4 h-4 text-orange-600" />
                    <span className="text-sm text-orange-800">
                      Subscription will cancel at the end of the current billing period
                    </span>
                  </div>
                )}
              </div>
            </Card>

            {/* Usage Statistics */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                This Month's Usage
              </h3>
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">API Requests</span>
                    <span className="font-medium text-gray-900">1,234</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-blue-600 h-2 rounded-full" style={{ width: '30%' }}></div>
                  </div>
                  <div className="text-xs text-gray-500">30% of quota used</div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Tokens</span>
                    <span className="font-medium text-gray-900">45.6K</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-green-600 h-2 rounded-full" style={{ width: '45%' }}></div>
                  </div>
                  <div className="text-xs text-gray-500">45% of quota used</div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Storage</span>
                    <span className="font-medium text-gray-900">23 GB</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-purple-600 h-2 rounded-full" style={{ width: '23%' }}></div>
                  </div>
                  <div className="text-xs text-gray-500">23% of quota used</div>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* FAQ Section */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-6">Frequently Asked Questions</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">How do I upgrade my plan?</h4>
              <p className="text-sm text-gray-600">
                You can upgrade your plan at any time from this page. Your new plan will take effect immediately, and you'll be charged a prorated amount for the current billing period.
              </p>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Can I cancel my subscription?</h4>
              <p className="text-sm text-gray-600">
                Yes, you can cancel your subscription at any time. You'll continue to have access until the end of your current billing period.
              </p>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 mb-2">What happens if I exceed my usage limits?</h4>
              <p className="text-sm text-gray-600">
                If you exceed your usage limits, you'll be charged for the additional usage at our standard overage rates. You can upgrade your plan to get higher limits.
              </p>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Can I change my billing cycle?</h4>
              <p className="text-sm text-gray-600">
                Yes, you can switch between monthly and yearly billing at any time. Yearly billing offers a 20% discount compared to monthly billing.
              </p>
            </div>
          </div>
        </Card>

        {/* Support Section */}
        <Card className="p-6 bg-gradient-to-r from-blue-50 to-purple-50">
          <div className="text-center">
            <CheckCircleIcon className="w-12 h-12 text-blue-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Need Help with Your Subscription?
            </h3>
            <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
              Our support team is here to help you with any questions about your subscription, billing, or account.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button variant="outline">
                <InformationCircleIcon className="w-4 h-4 mr-2" />
                View Documentation
              </Button>
              <Button>
                Contact Support
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </BillingLayout>
  );
}