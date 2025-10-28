/**
 * PayPal支付表单组件
 *
 * 集成PayPal JavaScript SDK进行支付处理。
 */

'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  CreditCardIcon,
  LockClosedIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolidIcon } from '@heroicons/react/24/solid';

import { PaymentProvider, PaymentIntentResponse } from '@/types/billing';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';

declare global {
  interface Window {
    paypal?: any;
  }
}

interface PayPalPaymentFormProps {
  amount: number;
  currency?: string;
  description?: string;
  onSuccess?: (paymentResult: any) => void;
  onError?: (error: Error) => void;
  onCancel?: () => void;
  className?: string;
}

interface PayPalScriptState {
  loaded: boolean;
  loading: boolean;
  error: string | null;
}

export const PayPalPaymentForm: React.FC<PayPalPaymentFormProps> = ({
  amount,
  currency = 'USD',
  description,
  onSuccess,
  onError,
  onCancel,
  className,
}) => {
  const [scriptState, setScriptState] = useState<PayPalScriptState>({
    loaded: false,
    loading: true,
    error: null,
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [paymentId, setPaymentId] = useState<string | null>(null);
  const [approvalUrl, setApprovalUrl] = useState<string | null>(null);

  const paypalContainerRef = useRef<HTMLDivElement>(null);

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  // Load PayPal SDK
  useEffect(() => {
    const loadPayPalScript = async () => {
      if (window.paypal) {
        setScriptState({ loaded: true, loading: false, error: null });
        return;
      }

      const clientId = process.env.NEXT_PUBLIC_PAYPAL_CLIENT_ID;
      if (!clientId) {
        setScriptState({
          loaded: false,
          loading: false,
          error: 'PayPal client ID is not configured',
        });
        return;
      }

      const script = document.createElement('script');
      script.src = `https://www.paypal.com/sdk/js?client-id=${clientId}&currency=${currency}`;
      script.async = true;
      script.onload = () => {
        setScriptState({ loaded: true, loading: false, error: null });
      };
      script.onerror = () => {
        setScriptState({
          loaded: false,
          loading: false,
          error: 'Failed to load PayPal SDK',
        });
      };

      document.body.appendChild(script);

      return () => {
        document.body.removeChild(script);
      };
    };

    loadPayPalScript();
  }, [currency]);

  // Create PayPal payment
  const createPayPalPayment = async () => {
    if (!window.paypal) {
      const error = new Error('PayPal SDK is not loaded');
      setMessage(error.message);
      if (onError) onError(error);
      return;
    }

    setIsProcessing(true);
    setMessage(null);

    try {
      const response = await fetch('/api/billing/payments/intent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          amount,
          paymentProvider: PaymentProvider.PAYPAL,
          description,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create PayPal payment');
      }

      const paymentIntent: PaymentIntentResponse = await response.json();

      if (paymentIntent.success && paymentIntent.approvalUrl) {
        setPaymentId(paymentIntent.paymentIntentId);
        setApprovalUrl(paymentIntent.approvalUrl);

        // Render PayPal buttons
        renderPayPalButtons(paymentIntent.approvalUrl);
      } else {
        throw new Error(paymentIntent.failureReason || 'Failed to create payment');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Payment creation failed';
      setMessage(errorMessage);
      if (onError) onError(new Error(errorMessage));
    } finally {
      setIsProcessing(false);
    }
  };

  // Render PayPal buttons
  const renderPayPalButtons = (approvalUrl: string) => {
    if (!window.paypal || !paypalContainerRef.current) return;

    paypalContainerRef.current.innerHTML = '';

    window.paypal.Buttons({
      createOrder: () => {
        return paymentId || '';
      },
      onApprove: async (data: any) => {
        setIsProcessing(true);
        setMessage('Processing payment...');

        try {
          const response = await fetch('/api/billing/payments/execute-paypal', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              paymentId: data.paymentID,
              payerId: data.payerID,
            }),
          });

          if (!response.ok) {
            throw new Error('Failed to execute PayPal payment');
          }

          const result = await response.json();
          setIsComplete(true);
          setMessage('Payment successful!');

          if (onSuccess) {
            onSuccess(result);
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Payment execution failed';
          setMessage(errorMessage);
          if (onError) onError(new Error(errorMessage));
        } finally {
          setIsProcessing(false);
        }
      },
      onError: (err: any) => {
        const errorMessage = err.message || 'PayPal payment error';
        setMessage(errorMessage);
        if (onError) onError(new Error(errorMessage));
        setIsProcessing(false);
      },
      onCancel: () => {
        setMessage('Payment was cancelled');
        if (onCancel) onCancel();
        setIsProcessing(false);
      },
    }).render(paypalContainerRef.current);
  };

  // Handle retry
  const handleRetry = () => {
    setMessage(null);
    setIsComplete(false);
    setPaymentId(null);
    setApprovalUrl(null);
    createPayPalPayment();
  };

  // Auto-create payment when SDK is loaded
  useEffect(() => {
    if (scriptState.loaded && !approvalUrl && !isProcessing) {
      createPayPalPayment();
    }
  }, [scriptState.loaded, approvalUrl, isProcessing]);

  if (scriptState.loading) {
    return (
      <Card className={cn('p-6', className)}>
        <div className="flex flex-col items-center justify-center py-8 space-y-4">
          <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Loading PayPal
            </h3>
            <p className="text-gray-600">
              Please wait while we load the secure payment form...
            </p>
          </div>
        </div>
      </Card>
    );
  }

  if (scriptState.error) {
    return (
      <Card className={cn('p-6', className)}>
        <div className="text-center space-y-4">
          <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto">
            <ExclamationTriangleIcon className="w-6 h-6 text-red-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Payment Error
            </h3>
            <p className="text-gray-600 mb-4">
              {scriptState.error}
            </p>
          </div>
          <div className="flex gap-3 justify-center">
            <Button variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            <Button onClick={() => window.location.reload()}>
              <ArrowPathIcon className="w-4 h-4 mr-2" />
              Try Again
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  if (isComplete) {
    return (
      <Card className={cn('p-6', className)}>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center py-8"
        >
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircleSolidIcon className="w-8 h-8 text-green-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Payment Successful!
          </h3>
          <p className="text-gray-600 mb-4">
            Your payment of {formatCurrency(amount, currency)} has been processed successfully.
          </p>
          <Button onClick={onCancel}>
            Continue
          </Button>
        </motion.div>
      </Card>
    );
  }

  return (
    <Card className={cn('p-6', className)}>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
            <CreditCardIcon className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Pay with PayPal</h3>
            <p className="text-sm text-gray-600">
              Complete your payment securely with PayPal
            </p>
          </div>
        </div>
      </div>

      {/* Payment Summary */}
      <Card className="p-4 bg-gray-50 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600">Amount</span>
          <span className="font-semibold text-gray-900">
            {formatCurrency(amount, currency)}
          </span>
        </div>
        {description && (
          <div className="text-sm text-gray-600">
            {description}
          </div>
        )}
      </Card>

      {/* PayPal Buttons Container */}
      <div className="mb-6">
        {!approvalUrl && isProcessing && (
          <div className="flex flex-col items-center justify-center py-8 space-y-4">
            <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Creating Payment
              </h3>
              <p className="text-gray-600">
                Please wait while we create your secure payment...
              </p>
            </div>
          </div>
        )}

        <div ref={paypalContainerRef} className="min-h-[48px]" />
      </div>

      {/* Error Message */}
      {message && (
        <Alert variant={message.includes('success') ? 'default' : 'destructive'} className="mb-6">
          {message.includes('success') ? (
            <CheckCircleIcon className="w-4 h-4" />
          ) : (
            <ExclamationTriangleIcon className="w-4 h-4" />
          )}
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}

      {/* Retry Button */}
      {!isProcessing && approvalUrl && message && message.includes('error') && (
        <div className="flex gap-3">
          <Button variant="outline" onClick={onCancel} className="flex-1">
            Cancel
          </Button>
          <Button onClick={handleRetry} className="flex-1 flex items-center gap-2">
            <ArrowPathIcon className="w-4 h-4" />
            Try Again
          </Button>
        </div>
      )}

      {/* Security Notice */}
      <div className="flex items-center gap-2 text-xs text-gray-500 bg-blue-50 p-3 rounded-lg">
        <LockClosedIcon className="w-4 h-4 text-blue-600" />
        <span>
          Your payment information is secure and encrypted by PayPal. We never store your financial details.
        </span>
      </div>

      {/* Cancel Button */}
      {onCancel && !isProcessing && !message && (
        <div className="mt-4">
          <Button variant="outline" onClick={onCancel} className="w-full">
            Cancel Payment
          </Button>
        </div>
      )}
    </Card>
  );
};

// PayPal Subscription Component
interface PayPalSubscriptionFormProps {
  planId: string;
  amount: number;
  currency?: string;
  description?: string;
  onSuccess?: (subscription: any) => void;
  onError?: (error: Error) => void;
  onCancel?: () => void;
  className?: string;
}

export const PayPalSubscriptionForm: React.FC<PayPalSubscriptionFormProps> = ({
  planId,
  amount,
  currency = 'USD',
  description,
  onSuccess,
  onError,
  onCancel,
  className,
}) => {
  const [scriptState, setScriptState] = useState<PayPalScriptState>({
    loaded: false,
    loading: true,
    error: null,
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [subscriptionId, setSubscriptionId] = useState<string | null>(null);

  const paypalContainerRef = useRef<HTMLDivElement>(null);

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  // Load PayPal SDK
  useEffect(() => {
    const loadPayPalScript = async () => {
      if (window.paypal) {
        setScriptState({ loaded: true, loading: false, error: null });
        return;
      }

      const clientId = process.env.NEXT_PUBLIC_PAYPAL_CLIENT_ID;
      if (!clientId) {
        setScriptState({
          loaded: false,
          loading: false,
          error: 'PayPal client ID is not configured',
        });
        return;
      }

      const script = document.createElement('script');
      script.src = `https://www.paypal.com/sdk/js?client-id=${clientId}&currency=${currency}&vault=true`;
      script.async = true;
      script.onload = () => {
        setScriptState({ loaded: true, loading: false, error: null });
      };
      script.onerror = () => {
        setScriptState({
          loaded: false,
          loading: false,
          error: 'Failed to load PayPal SDK',
        });
      };

      document.body.appendChild(script);

      return () => {
        document.body.removeChild(script);
      };
    };

    loadPayPalScript();
  }, [currency]);

  // Create PayPal subscription
  const createPayPalSubscription = async () => {
    if (!window.paypal) {
      const error = new Error('PayPal SDK is not loaded');
      setMessage(error.message);
      if (onError) onError(error);
      return;
    }

    setIsProcessing(true);
    setMessage(null);

    try {
      const response = await fetch('/api/billing/subscriptions/paypal', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          planId,
          paymentProvider: PaymentProvider.PAYPAL,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create PayPal subscription');
      }

      const subscriptionData = await response.json();

      if (subscriptionData.subscription_id) {
        setSubscriptionId(subscriptionData.subscription_id);

        // Render PayPal subscription buttons
        renderPayPalSubscriptionButtons(subscriptionData.subscription_id);
      } else {
        throw new Error('Failed to create subscription');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Subscription creation failed';
      setMessage(errorMessage);
      if (onError) onError(new Error(errorMessage));
    } finally {
      setIsProcessing(false);
    }
  };

  // Render PayPal subscription buttons
  const renderPayPalSubscriptionButtons = (subscriptionId: string) => {
    if (!window.paypal || !paypalContainerRef.current) return;

    paypalContainerRef.current.innerHTML = '';

    window.paypal.Buttons({
      style: {
        shape: 'rect',
        color: 'blue',
        layout: 'vertical',
        label: 'subscribe',
      },
      createSubscription: (data: any, actions: any) => {
        return actions.subscription.create({
          'plan_id': subscriptionId,
        });
      },
      onApprove: async (data: any, actions: any) => {
        setIsProcessing(true);
        setMessage('Processing subscription...');

        try {
          const response = await fetch('/api/billing/subscriptions/paypal/execute', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              subscriptionId: data.subscriptionID,
            }),
          });

          if (!response.ok) {
            throw new Error('Failed to execute PayPal subscription');
          }

          const result = await response.json();
          setIsComplete(true);
          setMessage('Subscription created successfully!');

          if (onSuccess) {
            onSuccess(result);
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Subscription execution failed';
          setMessage(errorMessage);
          if (onError) onError(new Error(errorMessage));
        } finally {
          setIsProcessing(false);
        }
      },
      onError: (err: any) => {
        const errorMessage = err.message || 'PayPal subscription error';
        setMessage(errorMessage);
        if (onError) onError(new Error(errorMessage));
        setIsProcessing(false);
      },
      onCancel: () => {
        setMessage('Subscription was cancelled');
        if (onCancel) onCancel();
        setIsProcessing(false);
      },
    }).render(paypalContainerRef.current);
  };

  // Auto-create subscription when SDK is loaded
  useEffect(() => {
    if (scriptState.loaded && !subscriptionId && !isProcessing) {
      createPayPalSubscription();
    }
  }, [scriptState.loaded, subscriptionId, isProcessing]);

  if (scriptState.loading) {
    return (
      <Card className={cn('p-6', className)}>
        <div className="flex flex-col items-center justify-center py-8 space-y-4">
          <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Loading PayPal
            </h3>
            <p className="text-gray-600">
              Please wait while we load the secure subscription form...
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className={cn('p-6', className)}>
      {/* Similar structure to PayPalPaymentForm but for subscriptions */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
            <CreditCardIcon className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">PayPal Subscription</h3>
            <p className="text-sm text-gray-600">
              Set up your subscription with PayPal
            </p>
          </div>
        </div>
      </div>

      {/* Payment Summary */}
      <Card className="p-4 bg-gray-50 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600">Monthly Amount</span>
          <span className="font-semibold text-gray-900">
            {formatCurrency(amount, currency)}
          </span>
        </div>
        {description && (
          <div className="text-sm text-gray-600">
            {description}
          </div>
        )}
      </Card>

      {/* PayPal Subscription Buttons */}
      <div className="mb-6">
        {!subscriptionId && isProcessing && (
          <div className="flex flex-col items-center justify-center py-8 space-y-4">
            <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Creating Subscription
              </h3>
              <p className="text-gray-600">
                Please wait while we create your secure subscription...
              </p>
            </div>
          </div>
        )}

        <div ref={paypalContainerRef} className="min-h-[48px]" />
      </div>

      {/* Error handling and other UI elements similar to PayPalPaymentForm */}
      {message && (
        <Alert variant={message.includes('success') ? 'default' : 'destructive'} className="mb-6">
          {message.includes('success') ? (
            <CheckCircleIcon className="w-4 h-4" />
          ) : (
            <ExclamationTriangleIcon className="w-4 h-4" />
          )}
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}

      <div className="flex items-center gap-2 text-xs text-gray-500 bg-blue-50 p-3 rounded-lg">
        <LockClosedIcon className="w-4 h-4 text-blue-600" />
        <span>
          Your subscription is secure and managed by PayPal. You can cancel anytime.
        </span>
      </div>
    </Card>
  );
};

export default PayPalPaymentForm;