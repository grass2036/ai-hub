/**
 * Stripe支付表单组件
 *
 * 集成Stripe Elements进行安全的支付处理。
 */

'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { loadStripe } from '@stripe/stripe-js';
import {
  PaymentElement,
  Elements,
  useStripe,
  useElements,
  AddressElement,
} from '@stripe/react-stripe-js';
import {
  CreditCardIcon,
  LockClosedIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolidIcon } from '@heroicons/react/24/solid';

import { PaymentProvider, PaymentIntentResponse } from '@/types/billing';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';

// Make sure to call `loadStripe` outside of a component's render to avoid
// recreating the `Stripe` object on every render.
if (!process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY) {
  throw new Error('NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY is not set');
}

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY);

interface StripePaymentFormProps {
  clientSecret: string;
  amount: number;
  currency?: string;
  description?: string;
  onSuccess?: (paymentResult: any) => void;
  onError?: (error: Error) => void;
  onCancel?: () => void;
  className?: string;
}

const PaymentFormContent: React.FC<{
  clientSecret: string;
  amount: number;
  currency?: string;
  description?: string;
  onSuccess?: (paymentResult: any) => void;
  onError?: (error: Error) => void;
  onCancel?: () => void;
}> = ({
  clientSecret,
  amount,
  currency = 'USD',
  description,
  onSuccess,
  onError,
  onCancel,
}) => {
  const stripe = useStripe();
  const elements = useElements();

  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [savePaymentMethod, setSavePaymentMethod] = useState(true);
  const [setAsDefault, setSetAsDefault] = useState(true);

  useEffect(() => {
    if (!stripe) return;

    const urlParams = new URLSearchParams(window.location.search);
    const paymentIntentClientSecret = urlParams.get('payment_intent_client_secret');

    if (paymentIntentClientSecret) {
      stripe.retrievePaymentIntent(paymentIntentClientSecret).then(({ paymentIntent }) => {
        switch (paymentIntent?.status) {
          case 'succeeded':
            setMessage('Payment succeeded!');
            setIsComplete(true);
            break;
          case 'processing':
            setMessage('Your payment is processing.');
            break;
          case 'requires_payment_method':
            setMessage('Your payment was not successful, please try again.');
            break;
          default:
            setMessage('Something went wrong.');
            break;
        }
      });
    }
  }, [stripe]);

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount / 100);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    setIsLoading(true);
    setMessage(null);

    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/billing/payment/success`,
        payment_method_data: {
          billing_details: {
            // You can add billing details here if needed
          },
        },
        setup_future_usage: savePaymentMethod ? 'off_session' : undefined,
      },
    });

    if (error) {
      if (error.type === 'card_error' || error.type === 'validation_error') {
        setMessage(error.message || 'An unexpected error occurred.');
      } else {
        setMessage('An unexpected error occurred.');
      }

      if (onError) {
        onError(new Error(error.message || 'Payment failed'));
      }
    } else {
      setMessage('Payment processing...');
      setIsComplete(true);
      if (onSuccess) {
        onSuccess({ status: 'processing' });
      }
    }

    setIsLoading(false);
  };

  const paymentElementOptions = {
    layout: 'tabs' as const,
    defaultValues: {
      billingDetails: {
        // You can set default billing details here
      },
    },
  };

  if (isComplete) {
    return (
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
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Payment Summary */}
      <Card className="p-4 bg-gray-50">
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

      {/* Address Element */}
      <div className="space-y-2">
        <Label htmlFor="address" className="text-sm font-medium text-gray-900">
          Billing Address
        </Label>
        <AddressElement
          id="address"
          options={{
            mode: 'billing',
            fields: {
              phone: 'always',
              email: 'always',
            },
            validation: {
              phone: {
                required: 'never',
              },
            },
          }}
        />
      </div>

      {/* Payment Element */}
      <div className="space-y-2">
        <Label htmlFor="payment-element" className="text-sm font-medium text-gray-900">
          Payment Information
        </Label>
        <PaymentElement
          id="payment-element"
          options={paymentElementOptions}
        />
      </div>

      {/* Payment Options */}
      <div className="space-y-3">
        <div className="flex items-center space-x-2">
          <Checkbox
            id="save-payment-method"
            checked={savePaymentMethod}
            onCheckedChange={(checked) => setSavePaymentMethod(checked as boolean)}
          />
          <Label htmlFor="save-payment-method" className="text-sm text-gray-700">
            Save payment method for future purchases
          </Label>
        </div>

        {savePaymentMethod && (
          <div className="flex items-center space-x-2">
            <Checkbox
              id="set-as-default"
              checked={setAsDefault}
              onCheckedChange={(checked) => setSetAsDefault(checked as boolean)}
            />
            <Label htmlFor="set-as-default" className="text-sm text-gray-700">
              Set as default payment method
            </Label>
          </div>
        )}
      </div>

      {/* Error Message */}
      {message && (
        <Alert variant={message.includes('success') ? 'default' : 'destructive'}>
          {message.includes('success') ? (
            <CheckCircleIcon className="w-4 h-4" />
          ) : (
            <ExclamationTriangleIcon className="w-4 h-4" />
          )}
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}

      {/* Security Notice */}
      <div className="flex items-center gap-2 text-xs text-gray-500 bg-blue-50 p-3 rounded-lg">
        <LockClosedIcon className="w-4 h-4 text-blue-600" />
        <span>
          Your payment information is secure and encrypted. We never store your card details.
        </span>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        {onCancel && (
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={isLoading}
            className="flex-1"
          >
            Cancel
          </Button>
        )}
        <Button
          type="submit"
          disabled={isLoading || !stripe || !elements}
          className="flex-1 flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <LockClosedIcon className="w-4 h-4" />
              Pay {formatCurrency(amount, currency)}
            </>
          )}
        </Button>
      </div>
    </form>
  );
};

export const StripePaymentForm: React.FC<StripePaymentFormProps> = ({
  clientSecret,
  amount,
  currency = 'USD',
  description,
  onSuccess,
  onError,
  onCancel,
  className,
}) => {
  const options = {
    clientSecret,
    appearance: {
      theme: 'stripe' as const,
      variables: {
        colorPrimary: '#0570de',
        colorBackground: '#ffffff',
        colorText: '#30313d',
        colorDanger: '#df1b41',
        fontFamily: 'system-ui, sans-serif',
        spacingUnit: '4px',
        borderRadius: '6px',
      },
    },
  };

  return (
    <Card className={cn('p-6', className)}>
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
            <CreditCardIcon className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Secure Payment</h3>
            <p className="text-sm text-gray-600">
              Complete your payment securely with Stripe
            </p>
          </div>
        </div>
      </div>

      <Elements stripe={stripePromise} options={options}>
        <PaymentFormContent
          clientSecret={clientSecret}
          amount={amount}
          currency={currency}
          description={description}
          onSuccess={onSuccess}
          onError={onError}
          onCancel={onCancel}
        />
      </Elements>
    </Card>
  );
};

// Payment Method Management Component
interface PaymentMethodManagerProps {
  onSuccess?: (paymentMethod: any) => void;
  onCancel?: () => void;
  className?: string;
}

export const PaymentMethodManager: React.FC<PaymentMethodManagerProps> = ({
  onSuccess,
  onCancel,
  className,
}) => {
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleAddPaymentMethod = async () => {
    setIsLoading(true);
    try {
      // Create a setup intent
      const response = await fetch('/api/billing/payments/setup-intent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      const data = await response.json();
      setClientSecret(data.clientSecret);
      setIsAddingNew(true);
    } catch (error) {
      console.error('Failed to create setup intent:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuccess = (paymentMethod: any) => {
    setIsAddingNew(false);
    setClientSecret(null);
    if (onSuccess) {
      onSuccess(paymentMethod);
    }
  };

  const handleCancel = () => {
    setIsAddingNew(false);
    setClientSecret(null);
    if (onCancel) {
      onCancel();
    }
  };

  if (isAddingNew && clientSecret) {
    return (
      <StripePaymentForm
        clientSecret={clientSecret}
        amount={0} // Setup intents don't require an amount
        description="Add payment method"
        onSuccess={handleSuccess}
        onError={(error) => console.error('Payment method error:', error)}
        onCancel={handleCancel}
        className={className}
      />
    );
  }

  return (
    <Card className={cn('p-6', className)}>
      <div className="text-center space-y-4">
        <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto">
          <CreditCardIcon className="w-8 h-8 text-blue-600" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Add Payment Method
          </h3>
          <p className="text-gray-600 mb-4">
            Add a new payment method to your account for future purchases.
          </p>
        </div>

        <div className="flex flex-col gap-3">
          <Button
            onClick={handleAddPaymentMethod}
            disabled={isLoading}
            className="flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Loading...
              </>
            ) : (
              <>
                <CreditCardIcon className="w-4 h-4" />
                Add Credit Card
              </>
            )}
          </Button>

          {onCancel && (
            <Button variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
        </div>

        <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
          <LockClosedIcon className="w-4 h-4" />
          <span>Secured by Stripe</span>
        </div>
      </div>
    </Card>
  );
};

export default StripePaymentForm;