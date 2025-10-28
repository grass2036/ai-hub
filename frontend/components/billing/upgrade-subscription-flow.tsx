/**
 * 订阅升级流程组件
 *
 * 处理订阅升级的完整���程，包括计划选择、支付确认、升级处理等。
 */

'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowRightIcon,
  CheckCircleIcon,
  CreditCardIcon,
  LockClosedIcon,
  SparklesIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolidIcon } from '@heroicons/react/24/solid';

import {
  Subscription,
  PricingPlan,
  PlanType,
  BillingCycle,
  PaymentProvider,
  CreateSubscriptionRequest,
} from '@/types/billing';
import { useBillingActions } from '@/store/billing-store';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { toast } from 'react-hot-toast';

interface UpgradeSubscriptionFlowProps {
  currentSubscription: Subscription;
  availablePlans: PricingPlan[];
  onComplete?: (newSubscription: Subscription) => void;
  onCancel?: () => void;
  className?: string;
}

type UpgradeStep = 'select-plan' | 'payment-method' | 'confirm-payment' | 'processing' | 'complete';

export const UpgradeSubscriptionFlow: React.FC<UpgradeSubscriptionFlowProps> = ({
  currentSubscription,
  availablePlans,
  onComplete,
  onCancel,
  className,
}) => {
  const [currentStep, setCurrentStep] = useState<UpgradeStep>('select-plan');
  const [selectedPlan, setSelectedPlan] = useState<PricingPlan | null>(null);
  const [billingCycle, setBillingCycle] = useState<BillingCycle>(currentSubscription.billingCycle);
  const [paymentProvider, setPaymentProvider] = useState<PaymentProvider>(PaymentProvider.STRIPE);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const actions = useBillingActions();

  // Filter available plans (exclude current plan and downgrade options)
  const upgradePlans = availablePlans.filter(plan => {
    const planTypeOrder = [PlanType.FREE, PlanType.PRO, PlanType.ENTERPRISE];
    const currentIndex = planTypeOrder.indexOf(currentSubscription.plan.type as PlanType);
    const planIndex = planTypeOrder.indexOf(plan.type);
    return planIndex > currentIndex && plan.billingCycle === billingCycle;
  });

  useEffect(() => {
    // Auto-select the first upgrade plan if available
    if (upgradePlans.length > 0 && !selectedPlan) {
      setSelectedPlan(upgradePlans[0]);
    }
  }, [upgradePlans, selectedPlan]);

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const calculateSavings = () => {
    if (!selectedPlan) return 0;

    const currentMonthlyPrice = currentSubscription.unitPrice;
    const newMonthlyPrice = selectedPlan.price;

    if (billingCycle === BillingCycle.YEARLY) {
      const currentYearlyPrice = currentMonthlyPrice * 12;
      const newYearlyPrice = newMonthlyPrice * 12 * 0.8; // 20% discount for yearly
      return currentYearlyPrice - newYearlyPrice;
    }

    return 0;
  };

  const handlePlanSelect = (plan: PricingPlan) => {
    setSelectedPlan(plan);
    setError(null);
  };

  const handlePaymentMethodSelect = (provider: PaymentProvider) => {
    setPaymentProvider(provider);
  };

  const handleProceedToPayment = () => {
    if (!selectedPlan) return;
    setCurrentStep('payment-method');
  };

  const handleConfirmPayment = async () => {
    if (!selectedPlan) return;

    setIsProcessing(true);
    setError(null);
    setCurrentStep('processing');

    try {
      // Create upgrade request
      const upgradeRequest: CreateSubscriptionRequest = {
        planType: selectedPlan.type,
        billingCycle,
        paymentProvider,
      };

      // Process upgrade
      const newSubscription = await actions.upgradeSubscription(
        currentSubscription.id,
        selectedPlan.type
      );

      setCurrentStep('complete');
      toast.success('Subscription upgraded successfully!');

      if (onComplete) {
        onComplete(newSubscription);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upgrade subscription');
      setCurrentStep('payment-method');
      toast.error('Failed to upgrade subscription');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    }
  };

  const resetFlow = () => {
    setCurrentStep('select-plan');
    setSelectedPlan(null);
    setError(null);
    setIsProcessing(false);
  };

  const renderStepIndicator = () => {
    const steps: { key: UpgradeStep; label: string }[] = [
      { key: 'select-plan', label: 'Select Plan' },
      { key: 'payment-method', label: 'Payment' },
      { key: 'confirm-payment', label: 'Confirm' },
      { key: 'processing', label: 'Processing' },
      { key: 'complete', label: 'Complete' },
    ];

    const currentStepIndex = steps.findIndex(step => step.key === currentStep);

    return (
      <div className="flex items-center justify-between mb-8">
        {steps.map((step, index) => (
          <div key={step.key} className="flex items-center">
            <div className={cn(
              'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors',
              index <= currentStepIndex
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-600'
            )}>
              {index < currentStepIndex ? (
                <CheckCircleIcon className="w-4 h-4" />
              ) : (
                index + 1
              )}
            </div>
            <span className={cn(
              'ml-2 text-sm font-medium',
              index <= currentStepIndex ? 'text-blue-600' : 'text-gray-600'
            )}>
              {step.label}
            </span>
            {index < steps.length - 1 && (
              <div className={cn(
                'w-12 h-0.5 ml-4 mr-2',
                index < currentStepIndex ? 'bg-blue-600' : 'bg-gray-200'
              )} />
            )}
          </div>
        ))}
      </div>
    );
  };

  const renderSelectPlanStep = () => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-6"
    >
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Choose Your New Plan
        </h3>
        <p className="text-gray-600">
          Select a plan that best fits your needs. You can upgrade at any time.
        </p>
      </div>

      {/* Billing Cycle Toggle */}
      <div className="flex justify-center">
        <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
          <button
            className={cn(
              'flex-1 py-2 px-4 text-sm font-medium rounded-md transition-all',
              billingCycle === BillingCycle.MONTHLY
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            )}
            onClick={() => setBillingCycle(BillingCycle.MONTHLY)}
          >
            Monthly
          </button>
          <button
            className={cn(
              'flex-1 py-2 px-4 text-sm font-medium rounded-md transition-all',
              billingCycle === BillingCycle.YEARLY
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            )}
            onClick={() => setBillingCycle(BillingCycle.YEARLY)}
          >
            Yearly
            <Badge variant="secondary" className="ml-1 text-xs">
              Save 20%
            </Badge>
          </button>
        </div>
      </div>

      {/* Plan Options */}
      <div className="grid grid-cols-1 gap-4">
        {upgradePlans.map((plan) => {
          const isSelected = selectedPlan?.id === plan.id;
          const monthlyPrice = billingCycle === BillingCycle.YEARLY
            ? plan.price * 12 * 0.8
            : plan.price;

          return (
            <Card
              key={plan.id}
              className={cn(
                'p-4 cursor-pointer transition-all border-2',
                isSelected
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              )}
              onClick={() => handlePlanSelect(plan)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h4 className="font-semibold text-gray-900">{plan.name}</h4>
                    {isSelected && (
                      <CheckCircleSolidIcon className="w-5 h-5 text-blue-600" />
                    )}
                  </div>
                  <p className="text-sm text-gray-600 mb-3">{plan.description}</p>

                  <div className="flex items-baseline gap-1 mb-3">
                    <span className="text-2xl font-bold text-gray-900">
                      ${monthlyPrice.toFixed(2)}
                    </span>
                    <span className="text-gray-600">
                      /mo{billingCycle === BillingCycle.YEARLY ? ' (billed yearly)' : ''}
                    </span>
                  </div>

                  {plan.trialDays > 0 && (
                    <div className="flex items-center gap-1 text-sm text-blue-600">
                      <SparklesIcon className="w-4 h-4" />
                      <span>{plan.trialDays} days trial</span>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex justify-between">
        <Button variant="outline" onClick={handleCancel}>
          Cancel
        </Button>
        <Button
          onClick={handleProceedToPayment}
          disabled={!selectedPlan}
          className="flex items-center gap-2"
        >
          Continue
          <ArrowRightIcon className="w-4 h-4" />
        </Button>
      </div>
    </motion.div>
  );

  const renderPaymentMethodStep = () => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-6"
    >
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Choose Payment Method
        </h3>
        <p className="text-gray-600">
          Select your preferred payment provider for the subscription upgrade.
        </p>
      </div>

      <RadioGroup value={paymentProvider} onValueChange={handlePaymentMethodSelect}>
        <div className="space-y-3">
          <Label
            htmlFor="stripe"
            className={cn(
              'flex items-center justify-between p-4 border-2 rounded-lg cursor-pointer transition-colors',
              paymentProvider === PaymentProvider.STRIPE
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            )}
          >
            <div className="flex items-center gap-3">
              <RadioGroupItem value="stripe" id="stripe" />
              <div>
                <div className="font-medium">Credit Card (Stripe)</div>
                <div className="text-sm text-gray-600">
                  Visa, Mastercard, American Express, and more
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <LockClosedIcon className="w-4 h-4" />
              Secure
            </div>
          </Label>

          <Label
            htmlFor="paypal"
            className={cn(
              'flex items-center justify-between p-4 border-2 rounded-lg cursor-pointer transition-colors',
              paymentProvider === PaymentProvider.PAYPAL
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            )}
          >
            <div className="flex items-center gap-3">
              <RadioGroupItem value="paypal" id="paypal" />
              <div>
                <div className="font-medium">PayPal</div>
                <div className="text-sm text-gray-600">
                  Pay with your PayPal account or balance
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <LockClosedIcon className="w-4 h-4" />
              Secure
            </div>
          </Label>
        </div>
      </RadioGroup>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex justify-between">
        <Button variant="outline" onClick={() => setCurrentStep('select-plan')}>
          Back
        </Button>
        <Button
          onClick={() => setCurrentStep('confirm-payment')}
          className="flex items-center gap-2"
        >
          Continue
          <ArrowRightIcon className="w-4 h-4" />
        </Button>
      </div>
    </motion.div>
  );

  const renderConfirmPaymentStep = () => {
    if (!selectedPlan) return null;

    const currentPrice = currentSubscription.unitPrice;
    const newPrice = billingCycle === BillingCycle.YEARLY
      ? selectedPlan.price * 0.8 // Apply yearly discount
      : selectedPlan.price;

    const priceDifference = newPrice - currentPrice;
    const savings = calculateSavings();

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="space-y-6"
      >
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Confirm Your Upgrade
          </h3>
          <p className="text-gray-600">
            Review your subscription upgrade details before confirming.
          </p>
        </div>

        <Card className="p-6">
          <h4 className="font-medium text-gray-900 mb-4">Upgrade Summary</h4>

          <div className="space-y-4">
            {/* Current Plan */}
            <div className="flex items-center justify-between py-2">
              <div>
                <div className="font-medium text-gray-900">Current Plan</div>
                <div className="text-sm text-gray-600">
                  {currentSubscription.plan.type} • {currentSubscription.billingCycle}
                </div>
              </div>
              <div className="text-right">
                <div className="font-medium text-gray-900">
                  {formatCurrency(currentPrice)}
                </div>
                <div className="text-sm text-gray-600">per month</div>
              </div>
            </div>

            <Separator />

            {/* New Plan */}
            <div className="flex items-center justify-between py-2">
              <div>
                <div className="font-medium text-gray-900">New Plan</div>
                <div className="text-sm text-gray-600">
                  {selectedPlan.name} • {billingCycle}
                </div>
              </div>
              <div className="text-right">
                <div className="font-medium text-blue-600">
                  {formatCurrency(newPrice)}
                </div>
                <div className="text-sm text-gray-600">
                  per month{billingCycle === BillingCycle.YEARLY ? ' (billed yearly)' : ''}
                </div>
              </div>
            </div>

            <Separator />

            {/* Price Difference */}
            <div className="flex items-center justify-between py-2">
              <div className="font-medium text-gray-900">Additional Cost</div>
              <div className="font-medium text-gray-900">
                +{formatCurrency(Math.abs(priceDifference))} per month
              </div>
            </div>

            {/* Savings */}
            {savings > 0 && (
              <div className="flex items-center justify-between py-2 bg-green-50 px-3 rounded-lg">
                <div className="font-medium text-green-700">Yearly Savings</div>
                <div className="font-medium text-green-700">
                  {formatCurrency(savings)}
                </div>
              </div>
            )}

            {/* Payment Provider */}
            <div className="flex items-center justify-between py-2 bg-gray-50 px-3 rounded-lg">
              <div className="font-medium text-gray-700">Payment Method</div>
              <div className="font-medium text-gray-900 capitalize">
                {paymentProvider === PaymentProvider.STRIPE ? 'Credit Card' : 'PayPal'}
              </div>
            </div>
          </div>
        </Card>

        {/* Trial Info */}
        {selectedPlan.trialDays > 0 && (
          <Alert>
            <SparklesIcon className="w-4 h-4" />
            <AlertDescription>
              You'll get {selectedPlan.trialDays} days free trial with this upgrade.
              You won't be charged until the trial period ends.
            </AlertDescription>
          </Alert>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="flex justify-between">
          <Button variant="outline" onClick={() => setCurrentStep('payment-method')}>
            Back
          </Button>
          <Button
            onClick={handleConfirmPayment}
            disabled={isProcessing}
            className="flex items-center gap-2"
          >
            <LockClosedIcon className="w-4 h-4" />
            Confirm Upgrade
          </Button>
        </div>
      </motion.div>
    );
  };

  const renderProcessingStep = () => (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center py-12 space-y-6"
    >
      <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Processing Your Upgrade
        </h3>
        <p className="text-gray-600">
          Please wait while we process your subscription upgrade...
        </p>
      </div>
    </motion.div>
  );

  const renderCompleteStep = () => (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center py-12 space-y-6 text-center"
    >
      <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
        <CheckCircleSolidIcon className="w-8 h-8 text-green-600" />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Upgrade Complete!
        </h3>
        <p className="text-gray-600 mb-4">
          Your subscription has been successfully upgraded to {selectedPlan?.name}.
        </p>
        <p className="text-sm text-gray-600">
          You'll receive a confirmation email shortly with your updated subscription details.
        </p>
      </div>
      <Button onClick={resetFlow} className="flex items-center gap-2">
        Go to Billing
        <ArrowRightIcon className="w-4 h-4" />
      </Button>
    </motion.div>
  );

  if (upgradePlans.length === 0) {
    return (
      <Card className={cn('p-6 text-center', className)}>
        <div className="space-y-4">
          <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto">
            <CheckCircleIcon className="w-6 h-6 text-gray-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              You're on our highest plan!
            </h3>
            <p className="text-gray-600">
              You're already enjoying all the features of our Enterprise plan.
            </p>
          </div>
          <Button variant="outline" onClick={onCancel}>
            Close
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <Card className={cn('p-6 max-w-2xl mx-auto', className)}>
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">Upgrade Subscription</h2>
          <Button variant="ghost" size="sm" onClick={handleCancel}>
            <XMarkIcon className="w-4 h-4" />
          </Button>
        </div>
        {renderStepIndicator()}
      </div>

      <AnimatePresence mode="wait">
        {currentStep === 'select-plan' && renderSelectPlanStep()}
        {currentStep === 'payment-method' && renderPaymentMethodStep()}
        {currentStep === 'confirm-payment' && renderConfirmPaymentStep()}
        {currentStep === 'processing' && renderProcessingStep()}
        {currentStep === 'complete' && renderCompleteStep()}
      </AnimatePresence>
    </Card>
  );
};

export default UpgradeSubscriptionFlow;