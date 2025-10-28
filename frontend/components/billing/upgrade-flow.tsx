/**
 * 订阅升级流程组件
 *
 * 处理用户升级/降级订阅的完整流程。
 */

'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// 类型导入
import { PricingPlan, PlanType, BillingCycle, PaymentProvider } from '@/types/billing';

// UI组件导入
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';

// Hooks导入
import { useSubscriptionManagement } from '@/store/billing-store';

// 图标导入
import {
  CheckCircleIcon,
  CreditCardIcon,
  CalendarIcon,
  ExclamationTriangleIcon,
  ArrowRightIcon,
  ArrowLeftIcon,
  SparklesIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';

interface UpgradeFlowProps {
  currentPlan: PlanType;
  availablePlans: PricingPlan[];
  onComplete: () => void;
  onCancel: () => void;
}

type Step = 'plan-selection' | 'billing-cycle' | 'payment-method' | 'confirmation' | 'processing';

interface PlanOption {
  plan: PricingPlan;
  isUpgrade: boolean;
  isDowngrade: boolean;
  priceDifference: number;
  savings: number;
}

const UpgradeFlow: React.FC<UpgradeFlowProps> = ({
  currentPlan,
  availablePlans,
  onComplete,
  onCancel,
}) => {
  const [currentStep, setCurrentStep] = useState<Step>('plan-selection');
  const [selectedPlanId, setSelectedPlanId] = useState<string>('');
  const [billingCycle, setBillingCycle] = useState<BillingCycle>('monthly');
  const [paymentProvider, setPaymentProvider] = useState<PaymentProvider>('stripe');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { actions } = useSubscriptionManagement();

  // 计算计划选项
  const planOptions: PlanOption[] = availablePlans
    .filter(plan => plan.billingCycle === billingCycle)
    .map(plan => {
      const currentPlanObj = availablePlans.find(p => p.type === currentPlan);
      const currentPrice = currentPlanObj?.price || 0;
      const isUpgrade = plan.price > currentPrice;
      const isDowngrade = plan.price < currentPrice;
      const priceDifference = Math.abs(plan.price - currentPrice);

      // 计算年度节省
      const savings = billingCycle === 'yearly' && isUpgrade ?
        (plan.price * 12 * 0.2) : 0; // 20% 年度折扣

      return {
        plan,
        isUpgrade,
        isDowngrade,
        priceDifference,
        savings,
      };
    })
    .filter(option => option.plan.id !== selectedPlanId || option.plan.type !== currentPlan);

  const selectedPlanOption = planOptions.find(option => option.plan.id === selectedPlanId);

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const handlePlanSelect = (planId: string) => {
    setSelectedPlanId(planId);
    setError(null);
  };

  const handleNext = async () => {
    if (currentStep === 'plan-selection' && !selectedPlanId) {
      setError('Please select a plan');
      return;
    }

    if (currentStep === 'plan-selection') {
      setCurrentStep('billing-cycle');
    } else if (currentStep === 'billing-cycle') {
      setCurrentStep('payment-method');
    } else if (currentStep === 'payment-method') {
      setCurrentStep('confirmation');
    }
    setError(null);
  };

  const handleBack = () => {
    if (currentStep === 'billing-cycle') {
      setCurrentStep('plan-selection');
    } else if (currentStep === 'payment-method') {
      setCurrentStep('billing-cycle');
    } else if (currentStep === 'confirmation') {
      setCurrentStep('payment-method');
    }
  };

  const handleConfirm = async () => {
    if (!selectedPlanOption) return;

    setIsProcessing(true);
    setError(null);

    try {
      // 这里应该调用实际的升级API
      // await actions.upgradeSubscription(subscriptionId, selectedPlanOption.plan.type as PlanType);

      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 2000));

      setCurrentStep('processing');

      // 模拟处理完成
      setTimeout(() => {
        onComplete();
      }, 2000);
    } catch (err) {
      setError('Failed to upgrade subscription. Please try again.');
      setIsProcessing(false);
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 'plan-selection':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-2">Choose Your New Plan</h3>
              <p className="text-sm text-gray-600">
                Select the plan that best fits your needs
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {planOptions.map((option) => (
                <motion.div
                  key={option.plan.id}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Card
                    className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
                      selectedPlanId === option.plan.id
                        ? 'ring-2 ring-blue-500 bg-blue-50'
                        : 'hover:border-blue-200'
                    }`}
                    onClick={() => handlePlanSelect(option.plan.id)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h4 className="font-semibold capitalize">{option.plan.name}</h4>
                            {option.isUpgrade && (
                              <Badge className="bg-green-100 text-green-800">
                                Upgrade
                              </Badge>
                            )}
                            {option.isDowngrade && (
                              <Badge variant="secondary" className="bg-orange-100 text-orange-800">
                                Downgrade
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 mb-3">{option.plan.description}</p>
                          <div className="flex items-center gap-2 text-sm text-gray-500">
                            <CalendarIcon className="w-4 h-4" />
                            <span>Billed {billingCycle}</span>
                          </div>
                        </div>

                        <div className="text-right">
                          <div className="text-2xl font-bold">
                            {formatCurrency(option.plan.price)}
                          </div>
                          <div className="text-sm text-gray-600">per {billingCycle === 'monthly' ? 'month' : 'year'}</div>
                          {option.priceDifference > 0 && (
                            <div className={`text-sm ${option.isUpgrade ? 'text-green-600' : 'text-orange-600'}`}>
                              {option.isUpgrade ? '+' : '-'}{formatCurrency(option.priceDifference)}/{billingCycle === 'monthly' ? 'month' : 'year'}
                            </div>
                          )}
                          {option.savings > 0 && (
                            <div className="text-sm text-green-600 font-medium">
                              Save {formatCurrency(option.savings)}/year
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="mt-3 pt-3 border-t">
                        <div className="flex flex-wrap gap-1">
                          {option.plan.features.slice(0, 3).map((feature, index) => (
                            <div key={index} className="flex items-center gap-1 text-xs text-gray-600">
                              <CheckCircleIcon className="w-3 h-3 text-green-600" />
                              {feature}
                            </div>
                          ))}
                          {option.plan.features.length > 3 && (
                            <div className="text-xs text-gray-500">
                              +{option.plan.features.length - 3} more
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>
        );

      case 'billing-cycle':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-2">Choose Billing Cycle</h3>
              <p className="text-sm text-gray-600">
                Select how often you'd like to be billed
              </p>
            </div>

            <RadioGroup value={billingCycle} onValueChange={(value) => setBillingCycle(value as BillingCycle)}>
              <div className="grid grid-cols-2 gap-4">
                <Card
                  className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
                    billingCycle === 'monthly'
                      ? 'ring-2 ring-blue-500 bg-blue-50'
                      : 'hover:border-blue-200'
                  }`}
                  onClick={() => setBillingCycle('monthly')}
                >
                  <CardContent className="p-4">
                    <div className="text-center">
                      <h4 className="font-semibold mb-1">Monthly</h4>
                      <div className="text-2xl font-bold mb-1">
                        {selectedPlanOption ? formatCurrency(selectedPlanOption.plan.price) : '$0'}
                      </div>
                      <p className="text-sm text-gray-600">per month</p>
                    </div>
                  </CardContent>
                </Card>

                <Card
                  className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
                    billingCycle === 'yearly'
                      ? 'ring-2 ring-blue-500 bg-blue-50'
                      : 'hover:border-blue-200'
                  }`}
                  onClick={() => setBillingCycle('yearly')}
                >
                  <CardContent className="p-4">
                    <div className="text-center">
                      <h4 className="font-semibold mb-1">Yearly</h4>
                      <div className="text-2xl font-bold mb-1">
                        {selectedPlanOption ? formatCurrency(selectedPlanOption.plan.price * 12) : '$0'}
                      </div>
                      <p className="text-sm text-gray-600">per year</p>
                      <Badge className="mt-2 bg-green-100 text-green-800">
                        Save 20%
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </RadioGroup>

            <Alert>
              <InformationCircleIcon className="w-4 h-4" />
              <AlertDescription>
                Yearly billing saves you 20% compared to monthly billing. You can change this anytime.
              </AlertDescription>
            </Alert>
          </div>
        );

      case 'payment-method':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-2">Payment Method</h3>
              <p className="text-sm text-gray-600">
                Choose your preferred payment provider
              </p>
            </div>

            <RadioGroup value={paymentProvider} onValueChange={(value) => setPaymentProvider(value as PaymentProvider)}>
              <div className="space-y-4">
                <Card
                  className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
                    paymentProvider === 'stripe'
                      ? 'ring-2 ring-blue-500 bg-blue-50'
                      : 'hover:border-blue-200'
                  }`}
                  onClick={() => setPaymentProvider('stripe')}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                        <CreditCardIcon className="w-5 h-5 text-purple-600" />
                      </div>
                      <div>
                        <h4 className="font-semibold">Stripe</h4>
                        <p className="text-sm text-gray-600">Secure card payments</p>
                      </div>
                      {paymentProvider === 'stripe' && (
                        <CheckCircleIcon className="w-5 h-5 text-blue-600 ml-auto" />
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card
                  className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
                    paymentProvider === 'paypal'
                      ? 'ring-2 ring-blue-500 bg-blue-50'
                      : 'hover:border-blue-200'
                  }`}
                  onClick={() => setPaymentProvider('paypal')}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                        <CreditCardIcon className="w-5 h-5 text-blue-600" />
                      </div>
                      <div>
                        <h4 className="font-semibold">PayPal</h4>
                        <p className="text-sm text-gray-600">Pay with PayPal or card</p>
                      </div>
                      {paymentProvider === 'paypal' && (
                        <CheckCircleIcon className="w-5 h-5 text-blue-600 ml-auto" />
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </RadioGroup>

            <Alert>
              <InformationCircleIcon className="w-4 h-4" />
              <AlertDescription>
                All payment methods are secure and PCI compliant. Your payment information is never stored on our servers.
              </AlertDescription>
            </Alert>
          </div>
        );

      case 'confirmation':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-2">Review Your Changes</h3>
              <p className="text-sm text-gray-600">
                Please confirm your subscription changes
              </p>
            </div>

            <Card>
              <CardContent className="p-4">
                <div className="space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b">
                    <div>
                      <div className="font-semibold capitalize">Current Plan</div>
                      <div className="text-sm text-gray-600 capitalize">{currentPlan}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold">
                        {formatCurrency(availablePlans.find(p => p.type === currentPlan)?.price || 0)}
                      </div>
                      <div className="text-sm text-gray-600">per {billingCycle}</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pb-3 border-b">
                    <div>
                      <div className="font-semibold capitalize">New Plan</div>
                      <div className="text-sm text-gray-600 capitalize">
                        {selectedPlanOption?.plan.name}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold">
                        {selectedPlanOption ? formatCurrency(selectedPlanOption.plan.price) : '$0'}
                      </div>
                      <div className="text-sm text-gray-600">per {billingCycle}</div>
                    </div>
                  </div>

                  {selectedPlanOption && selectedPlanOption.priceDifference > 0 && (
                    <div className="flex items-center justify-between pt-2">
                      <div className="font-medium">
                        {selectedPlanOption.isUpgrade ? 'Additional Cost' : 'Savings'}
                      </div>
                      <div className={`font-bold ${selectedPlanOption.isUpgrade ? 'text-red-600' : 'text-green-600'}`}>
                        {selectedPlanOption.isUpgrade ? '+' : '-'}
                        {formatCurrency(selectedPlanOption.priceDifference)}/{billingCycle === 'monthly' ? 'month' : 'year'}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-2">
                    <div className="font-medium">Payment Method</div>
                    <div className="capitalize">{paymentProvider}</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Alert>
              <InformationCircleIcon className="w-4 h-4" />
              <AlertDescription>
                Your changes will take effect immediately. You'll be charged the prorated amount for this billing cycle.
              </AlertDescription>
            </Alert>
          </div>
        );

      case 'processing':
        return (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <SparklesIcon className="w-8 h-8 text-blue-600 animate-pulse" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Processing Your Upgrade</h3>
            <p className="text-sm text-gray-600 mb-4">
              Please wait while we update your subscription...
            </p>
            <Progress value={75} className="w-full max-w-md mx-auto" />
          </div>
        );

      default:
        return null;
    }
  };

  const getStepNumber = () => {
    switch (currentStep) {
      case 'plan-selection': return 1;
      case 'billing-cycle': return 2;
      case 'payment-method': return 3;
      case 'confirmation': return 4;
      case 'processing': return 5;
      default: return 1;
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case 'plan-selection': return selectedPlanId !== '';
      case 'billing-cycle': return true;
      case 'payment-method': return true;
      case 'confirmation': return true;
      case 'processing': return false;
      default: return false;
    }
  };

  return (
    <div className="space-y-6">
      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">Step {getStepNumber()} of 4</span>
          <span className="text-gray-600 capitalize">
            {currentStep.replace('-', ' ')}
          </span>
        </div>
        <Progress value={(getStepNumber() - 1) * 25} className="h-2" />
      </div>

      {/* Error Display */}
      {error && (
        <Alert className="bg-red-50 border-red-200">
          <ExclamationTriangleIcon className="w-4 h-4 text-red-600" />
          <AlertDescription className="text-red-800">{error}</AlertDescription>
        </Alert>
      )}

      {/* Step Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.2 }}
        >
          {renderStepContent()}
        </motion.div>
      </AnimatePresence>

      {/* Actions */}
      <div className="flex justify-between pt-4">
        <div className="flex gap-3">
          {currentStep !== 'plan-selection' && currentStep !== 'processing' && (
            <Button variant="outline" onClick={handleBack} disabled={isProcessing}>
              <ArrowLeftIcon className="w-4 h-4 mr-2" />
              Back
            </Button>
          )}
          <Button variant="outline" onClick={onCancel} disabled={isProcessing}>
            Cancel
          </Button>
        </div>

        {currentStep === 'confirmation' && selectedPlanOption ? (
          <Button onClick={handleConfirm} disabled={isProcessing} className="bg-green-600 hover:bg-green-700">
            {isProcessing ? 'Processing...' : 'Confirm Upgrade'}
          </Button>
        ) : currentStep !== 'processing' ? (
          <Button onClick={handleNext} disabled={!canProceed() || isProcessing}>
            {currentStep === 'plan-selection' ? 'Continue to Billing' :
             currentStep === 'billing-cycle' ? 'Continue to Payment' :
             currentStep === 'payment-method' ? 'Review Changes' : 'Continue'}
            <ArrowRightIcon className="w-4 h-4 ml-2" />
          </Button>
        ) : null}
      </div>
    </div>
  );
};

export default UpgradeFlow;