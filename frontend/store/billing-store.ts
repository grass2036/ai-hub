/**
 * 计费系统状态管理
 *
 * 使用Zustand管理计费相关的状态，包括订阅、支付、使用量、发票等。
 */

import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

// API客户端
import { apiClient } from '@/lib/api-client';

// 类型定义
import {
  BillingState,
  BillingActions,
  PlanType,
  BillingCycle,
  PaymentProvider,
  UsageType,
  CreateSubscriptionRequest,
  PaymentIntentRequest,
  PaymentIntentResponse,
  PaymentConfirmRequest,
  UsageTrackingRequest,
  InvoiceGenerateRequest,
  Subscription,
  PricingPlan,
  PaymentMethod,
  Payment,
  Invoice,
  UsageStats,
  QuotaInfo,
  BillingSummary,
  BillingError
} from '@/types/billing';

// 初始状态
const initialState: Omit<BillingState, 'actions'> = {
  // 订阅状态
  subscriptions: [],
  currentSubscription: null,
  availablePlans: [],
  subscriptionLoading: false,
  subscriptionError: null,

  // 支付状态
  paymentMethods: [],
  payments: [],
  paymentLoading: false,
  paymentError: null,

  // 使用量状态
  usageStats: null,
  quotaInfo: null,
  usageLoading: false,
  usageError: null,

  // 发票状态
  invoices: [],
  invoiceLoading: false,
  invoiceError: null,

  // 计费摘要
  billingSummary: null,
  summaryLoading: false,
  summaryError: null,
};

// 计费Store
export const useBillingStore = create<BillingState & { actions: BillingActions }>()(
  devtools(
    subscribeWithSelector(
      immer((set, get) => ({
        ...initialState,

        actions: {
          // 订阅操作
          createSubscription: async (request: CreateSubscriptionRequest) => {
            set((state) => {
              state.subscriptionLoading = true;
              state.subscriptionError = null;
            });

            try {
              const response = await apiClient.post('/billing/subscriptions', request);
              const newSubscription: Subscription = response.data;

              set((state) => {
                state.subscriptionLoading = false;
                state.subscriptions.push(newSubscription);
                if (!state.currentSubscription || newSubscription.status === 'active') {
                  state.currentSubscription = newSubscription;
                }
              });

              return newSubscription;
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'CREATE_SUBSCRIPTION_ERROR',
                message: error.response?.data?.message || 'Failed to create subscription',
                details: error.response?.data?.details
              };

              set((state) => {
                state.subscriptionLoading = false;
                state.subscriptionError = billingError.message;
              });

              throw billingError;
            }
          },

          cancelSubscription: async (subscriptionId: string, atPeriodEnd: boolean) => {
            set((state) => {
              state.subscriptionLoading = true;
              state.subscriptionError = null;
            });

            try {
              await apiClient.post(`/billing/subscriptions/${subscriptionId}/cancel`, {
                atPeriodEnd
              });

              set((state) => {
                state.subscriptionLoading = false;
                const subscription = state.subscriptions.find(s => s.id === subscriptionId);
                if (subscription) {
                  subscription.status = atPeriodEnd ? 'active' : 'cancelled';
                  subscription.cancelAtPeriodEnd = atPeriodEnd;
                }
                if (state.currentSubscription?.id === subscriptionId) {
                  state.currentSubscription!.status = atPeriodEnd ? 'active' : 'cancelled';
                  state.currentSubscription!.cancelAtPeriodEnd = atPeriodEnd;
                }
              });
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'CANCEL_SUBSCRIPTION_ERROR',
                message: error.response?.data?.message || 'Failed to cancel subscription',
                details: error.response?.data?.details
              };

              set((state) => {
                state.subscriptionLoading = false;
                state.subscriptionError = billingError.message;
              });

              throw billingError;
            }
          },

          upgradeSubscription: async (subscriptionId: string, newPlanType: PlanType) => {
            set((state) => {
              state.subscriptionLoading = true;
              state.subscriptionError = null;
            });

            try {
              const response = await apiClient.post(`/billing/subscriptions/${subscriptionId}/upgrade`, {
                newPlanType
              });
              const updatedSubscription: Subscription = response.data;

              set((state) => {
                state.subscriptionLoading = false;
                const index = state.subscriptions.findIndex(s => s.id === subscriptionId);
                if (index !== -1) {
                  state.subscriptions[index] = updatedSubscription;
                }
                if (state.currentSubscription?.id === subscriptionId) {
                  state.currentSubscription = updatedSubscription;
                }
              });

              return updatedSubscription;
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'UPGRADE_SUBSCRIPTION_ERROR',
                message: error.response?.data?.message || 'Failed to upgrade subscription',
                details: error.response?.data?.details
              };

              set((state) => {
                state.subscriptionLoading = false;
                state.subscriptionError = billingError.message;
              });

              throw billingError;
            }
          },

          getSubscriptions: async () => {
            set((state) => {
              state.subscriptionLoading = true;
              state.subscriptionError = null;
            });

            try {
              const response = await apiClient.get('/billing/subscriptions');
              const subscriptions: Subscription[] = response.data.subscriptions;

              set((state) => {
                state.subscriptionLoading = false;
                state.subscriptions = subscriptions;
                state.currentSubscription = subscriptions.find(s => s.status === 'active') || null;
              });

              return subscriptions;
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'GET_SUBSCRIPTIONS_ERROR',
                message: error.response?.data?.message || 'Failed to fetch subscriptions',
                details: error.response?.data?.details
              };

              set((state) => {
                state.subscriptionLoading = false;
                state.subscriptionError = billingError.message;
              });

              throw billingError;
            }
          },

          getCurrentSubscription: async () => {
            set((state) => {
              state.subscriptionLoading = true;
              state.subscriptionError = null;
            });

            try {
              const response = await apiClient.get('/billing/subscriptions');
              const subscriptions: Subscription[] = response.data.subscriptions;
              const currentSubscription = subscriptions.find(s => s.status === 'active') || null;

              set((state) => {
                state.subscriptionLoading = false;
                state.currentSubscription = currentSubscription;
              });

              return currentSubscription;
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'GET_CURRENT_SUBSCRIPTION_ERROR',
                message: error.response?.data?.message || 'Failed to fetch current subscription',
                details: error.response?.data?.details
              };

              set((state) => {
                state.subscriptionLoading = false;
                state.subscriptionError = billingError.message;
              });

              throw billingError;
            }
          },

          getAvailablePlans: async () => {
            set((state) => {
              state.subscriptionLoading = true;
              state.subscriptionError = null;
            });

            try {
              const response = await apiClient.get('/billing/plans');
              const plans: PricingPlan[] = response.data.plans;

              set((state) => {
                state.subscriptionLoading = false;
                state.availablePlans = plans;
              });

              return plans;
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'GET_PLANS_ERROR',
                message: error.response?.data?.message || 'Failed to fetch available plans',
                details: error.response?.data?.details
              };

              set((state) => {
                state.subscriptionLoading = false;
                state.subscriptionError = billingError.message;
              });

              throw billingError;
            }
          },

          // 支付操作
          createPaymentIntent: async (request: PaymentIntentRequest): Promise<PaymentIntentResponse> => {
            set((state) => {
              state.paymentLoading = true;
              state.paymentError = null;
            });

            try {
              const response = await apiClient.post('/billing/payments/intent', request);
              const paymentIntent: PaymentIntentResponse = response.data;

              set((state) => {
                state.paymentLoading = false;
              });

              return paymentIntent;
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'CREATE_PAYMENT_INTENT_ERROR',
                message: error.response?.data?.message || 'Failed to create payment intent',
                details: error.response?.data?.details
              };

              set((state) => {
                state.paymentLoading = false;
                state.paymentError = billingError.message;
              });

              throw billingError;
            }
          },

          confirmPayment: async (request: PaymentConfirmRequest) => {
            set((state) => {
              state.paymentLoading = true;
              state.paymentError = null;
            });

            try {
              await apiClient.post('/billing/payments/confirm', request);

              set((state) => {
                state.paymentLoading = false;
              });
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'CONFIRM_PAYMENT_ERROR',
                message: error.response?.data?.message || 'Failed to confirm payment',
                details: error.response?.data?.details
              };

              set((state) => {
                state.paymentLoading = false;
                state.paymentError = billingError.message;
              });

              throw billingError;
            }
          },

          getPaymentMethods: async () => {
            set((state) => {
              state.paymentLoading = true;
              state.paymentError = null;
            });

            try {
              const response = await apiClient.get('/billing/payments/methods');
              const paymentMethods: PaymentMethod[] = response.data.methods;

              set((state) => {
                state.paymentLoading = false;
                state.paymentMethods = paymentMethods;
              });

              return paymentMethods;
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'GET_PAYMENT_METHODS_ERROR',
                message: error.response?.data?.message || 'Failed to fetch payment methods',
                details: error.response?.data?.details
              };

              set((state) => {
                state.paymentLoading = false;
                state.paymentError = billingError.message;
              });

              throw billingError;
            }
          },

          getPaymentHistory: async () => {
            set((state) => {
              state.paymentLoading = true;
              state.paymentError = null;
            });

            try {
              const response = await apiClient.get('/billing/payments');
              const payments: Payment[] = response.data.payments;

              set((state) => {
                state.paymentLoading = false;
                state.payments = payments;
              });

              return payments;
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'GET_PAYMENT_HISTORY_ERROR',
                message: error.response?.data?.message || 'Failed to fetch payment history',
                details: error.response?.data?.details
              };

              set((state) => {
                state.paymentLoading = false;
                state.paymentError = billingError.message;
              });

              throw billingError;
            }
          },

          // 使用量操作
          trackUsage: async (request: UsageTrackingRequest) => {
            try {
              await apiClient.post('/billing/usage/track', request);
            } catch (error) {
              // 使用量跟踪失败不应该阻断用户操作，只记录错误
              console.error('Failed to track usage:', error);
            }
          },

          getUsageStats: async (startDate: string, endDate: string, usageType?: UsageType) => {
            set((state) => {
              state.usageLoading = true;
              state.usageError = null;
            });

            try {
              const params = new URLSearchParams({
                start_date: startDate,
                end_date: endDate,
                ...(usageType && { usage_type: usageType })
              });

              const response = await apiClient.get(`/billing/usage/stats?${params}`);
              const usageStats: UsageStats = response.data;

              set((state) => {
                state.usageLoading = false;
                state.usageStats = usageStats;
              });

              return usageStats;
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'GET_USAGE_STATS_ERROR',
                message: error.response?.data?.message || 'Failed to fetch usage statistics',
                details: error.response?.data?.details
              };

              set((state) => {
                state.usageLoading = false;
                state.usageError = billingError.message;
              });

              throw billingError;
            }
          },

          getQuotaStatus: async () => {
            set((state) => {
              state.usageLoading = true;
              state.usageError = null;
            });

            try {
              const response = await apiClient.get('/billing/quota');
              const quotaInfo: QuotaInfo = response.data;

              set((state) => {
                state.usageLoading = false;
                state.quotaInfo = quotaInfo;
              });

              return quotaInfo;
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'GET_QUOTA_STATUS_ERROR',
                message: error.response?.data?.message || 'Failed to fetch quota status',
                details: error.response?.data?.details
              };

              set((state) => {
                state.usageLoading = false;
                state.usageError = billingError.message;
              });

              throw billingError;
            }
          },

          // 发票操作
          generateInvoice: async (request: InvoiceGenerateRequest) => {
            set((state) => {
              state.invoiceLoading = true;
              state.invoiceError = null;
            });

            try {
              const response = await apiClient.post('/billing/invoices/generate', request);
              const invoice: Invoice = response.data.invoice;

              set((state) => {
                state.invoiceLoading = false;
                state.invoices.unshift(invoice);
              });

              return invoice;
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'GENERATE_INVOICE_ERROR',
                message: error.response?.data?.message || 'Failed to generate invoice',
                details: error.response?.data?.details
              };

              set((state) => {
                state.invoiceLoading = false;
                state.invoiceError = billingError.message;
              });

              throw billingError;
            }
          },

          getInvoices: async () => {
            set((state) => {
              state.invoiceLoading = true;
              state.invoiceError = null;
            });

            try {
              const response = await apiClient.get('/billing/invoices');
              const invoices: Invoice[] = response.data.invoices;

              set((state) => {
                state.invoiceLoading = false;
                state.invoices = invoices;
              });

              return invoices;
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'GET_INVOICES_ERROR',
                message: error.response?.data?.message || 'Failed to fetch invoices',
                details: error.response?.data?.details
              };

              set((state) => {
                state.invoiceLoading = false;
                state.invoiceError = billingError.message;
              });

              throw billingError;
            }
          },

          downloadInvoice: async (invoiceId: string): Promise<Blob> => {
            set((state) => {
              state.invoiceLoading = true;
              state.invoiceError = null;
            });

            try {
              const response = await apiClient.get(`/billing/invoices/${invoiceId}/pdf`, {
                responseType: 'blob'
              });

              set((state) => {
                state.invoiceLoading = false;
              });

              return response.data;
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'DOWNLOAD_INVOICE_ERROR',
                message: error.response?.data?.message || 'Failed to download invoice',
                details: error.response?.data?.details
              };

              set((state) => {
                state.invoiceLoading = false;
                state.invoiceError = billingError.message;
              });

              throw billingError;
            }
          },

          // 摘要操作
          getBillingSummary: async () => {
            set((state) => {
              state.summaryLoading = true;
              state.summaryError = null;
            });

            try {
              const response = await apiClient.get('/billing/summary');
              const billingSummary: BillingSummary = response.data;

              set((state) => {
                state.summaryLoading = false;
                state.billingSummary = billingSummary;
              });

              return billingSummary;
            } catch (error) {
              const billingError: BillingError = {
                code: error.response?.data?.code || 'GET_BILLING_SUMMARY_ERROR',
                message: error.response?.data?.message || 'Failed to fetch billing summary',
                details: error.response?.data?.details
              };

              set((state) => {
                state.summaryLoading = false;
                state.summaryError = billingError.message;
              });

              throw billingError;
            }
          },

          // 清理操作
          clearErrors: () => {
            set((state) => {
              state.subscriptionError = null;
              state.paymentError = null;
              state.usageError = null;
              state.invoiceError = null;
              state.summaryError = null;
            });
          },

          resetState: () => {
            set((state) => {
              Object.assign(state, initialState);
            });
          },
        },
      }))
    ),
    { name: 'billing-store' }
  )
);

// 选择器hooks
export const useSubscriptions = () => useBillingStore((state) => state.subscriptions);
export const useCurrentSubscription = () => useBillingStore((state) => state.currentSubscription);
export const useAvailablePlans = () => useBillingStore((state) => state.availablePlans);
export const useSubscriptionLoading = () => useBillingStore((state) => state.subscriptionLoading);
export const useSubscriptionError = () => useBillingStore((state) => state.subscriptionError);

export const usePaymentMethods = () => useBillingStore((state) => state.paymentMethods);
export const usePayments = () => useBillingStore((state) => state.payments);
export const usePaymentLoading = () => useBillingStore((state) => state.paymentLoading);
export const usePaymentError = () => useBillingStore((state) => state.paymentError);

export const useUsageStats = () => useBillingStore((state) => state.usageStats);
export const useQuotaInfo = () => useBillingStore((state) => state.quotaInfo);
export const useUsageLoading = () => useBillingStore((state) => state.usageLoading);
export const useUsageError = () => useBillingStore((state) => state.usageError);

export const useInvoices = () => useBillingStore((state) => state.invoices);
export const useInvoiceLoading = () => useBillingStore((state) => state.invoiceLoading);
export const useInvoiceError = () => useBillingStore((state) => state.invoiceError);

export const useBillingSummary = () => useBillingStore((state) => state.billingSummary);
export const useSummaryLoading = () => useBillingStore((state) => state.summaryLoading);
export const useSummaryError = () => useBillingStore((state) => state.summaryError);

export const useBillingActions = () => useBillingStore((state) => state.actions);

// 复合hooks
export const useBillingData = () => {
  const currentSubscription = useCurrentSubscription();
  const billingSummary = useBillingSummary();
  const quotaInfo = useQuotaInfo();
  const availablePlans = useAvailablePlans();
  const subscriptionLoading = useSubscriptionLoading();
  const summaryLoading = useSummaryLoading();
  const usageLoading = useUsageLoading();

  return {
    currentSubscription,
    billingSummary,
    quotaInfo,
    availablePlans,
    loading: subscriptionLoading || summaryLoading || usageLoading,
  };
};

export const useSubscriptionManagement = () => {
  const currentSubscription = useCurrentSubscription();
  const availablePlans = useAvailablePlans();
  const subscriptionLoading = useSubscriptionLoading();
  const subscriptionError = useSubscriptionError();
  const actions = useBillingActions();

  return {
    currentSubscription,
    availablePlans,
    loading: subscriptionLoading,
    error: subscriptionError,
    actions,
  };
};

export const usePaymentManagement = () => {
  const paymentMethods = usePaymentMethods();
  const payments = usePayments();
  const paymentLoading = usePaymentLoading();
  const paymentError = usePaymentError();
  const actions = useBillingActions();

  return {
    paymentMethods,
    payments,
    loading: paymentLoading,
    error: paymentError,
    actions,
  };
};

export const useUsageManagement = () => {
  const usageStats = useUsageStats();
  const quotaInfo = useQuotaInfo();
  const usageLoading = useUsageLoading();
  const usageError = useUsageError();
  const actions = useBillingActions();

  return {
    usageStats,
    quotaInfo,
    loading: usageLoading,
    error: usageError,
    actions,
  };
};

export const useInvoiceManagement = () => {
  const invoices = useInvoices();
  const invoiceLoading = useInvoiceLoading();
  const invoiceError = useInvoiceError();
  const actions = useBillingActions();

  return {
    invoices,
    loading: invoiceLoading,
    error: invoiceError,
    actions,
  };
};