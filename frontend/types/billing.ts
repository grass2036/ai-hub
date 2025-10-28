/**
 * 计费系统TypeScript类型定义
 *
 * 定义计费相关的所有类型，包括订阅、支付、使用量、发票等。
 */

// ���础枚举类型
export enum PlanType {
  FREE = 'free',
  PRO = 'pro',
  ENTERPRISE = 'enterprise'
}

export enum BillingCycle {
  MONTHLY = 'monthly',
  YEARLY = 'yearly'
}

export enum PaymentProvider {
  STRIPE = 'stripe',
  PAYPAL = 'paypal'
}

export enum PaymentStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
  REFUNDED = 'refunded'
}

export enum SubscriptionStatus {
  ACTIVE = 'active',
  CANCELLED = 'cancelled',
  EXPIRED = 'expired',
  TRIAL = 'trial',
  PAST_DUE = 'past_due',
  UNPAID = 'unpaid'
}

export enum InvoiceStatus {
  DRAFT = 'draft',
  PENDING = 'pending',
  PAID = 'paid',
  PARTIALLY_PAID = 'partially_paid',
  OVERDUE = 'overdue',
  VOID = 'void',
  REFUNDED = 'refunded'
}

export enum UsageType {
  API_CALL = 'api_call',
  TOKEN_USAGE = 'token_usage',
  STORAGE = 'storage',
  BANDWIDTH = 'bandwidth'
}

export enum QuotaType {
  API_CALLS = 'api_calls',
  TOKENS = 'tokens',
  STORAGE_GB = 'storage_gb',
  REQUESTS_PER_MINUTE = 'requests_per_minute'
}

// 基础数据类型
export interface Currency {
  code: string;
  symbol: string;
  rate: number;
}

export interface PricingPlan {
  id: string;
  name: string;
  type: PlanType;
  billingCycle: BillingCycle;
  price: number;
  currency: string;
  description?: string;
  features: string[];
  popular?: boolean;
  trialDays: number;
  setupFee: number;
  isActive: boolean;
  metadata: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface Subscription {
  id: string;
  userId: string;
  planId: string;
  status: SubscriptionStatus;
  billingCycle: BillingCycle;
  currentPeriodStart: string;
  currentPeriodEnd: string;
  trialStart?: string;
  trialEnd?: string;
  cancelledAt?: string;
  cancelAtPeriodEnd: boolean;
  autoRenew: boolean;
  unitPrice: number;
  quantity: number;
  setupFeePaid: boolean;
  metadata: Record<string, any>;
  createdAt: string;
  updatedAt: string;

  // 计算属性
  isActive: boolean;
  isTrial: boolean;
  isExpired: boolean;
  daysUntilRenewal: number;
  daysInTrial: number;
}

export interface PaymentMethod {
  id: string;
  userId: string;
  provider: PaymentProvider;
  type: string;
  last4?: string;
  expiryMonth?: number;
  expiryYear?: number;
  brand?: string;
  country?: string;
  isDefault: boolean;
  metadata: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface Payment {
  id: string;
  userId: string;
  invoiceId?: string;
  paymentMethod: string;
  paymentIntentId?: string;
  transactionId?: string;
  gateway: PaymentProvider;
  status: PaymentStatus;
  amount: number;
  currency: string;
  feeAmount: number;
  netAmount: number;
  createdAt: string;
  updatedAt: string;
  processedAt?: string;
  failureReason?: string;
  gatewayResponse?: Record<string, any>;
  metadata: Record<string, any>;

  // 计算属性
  isSuccessful: boolean;
  isFailed: boolean;
}

export interface Invoice {
  id: string;
  userId: string;
  subscriptionId?: string;
  invoiceNumber: string;
  status: InvoiceStatus;
  issuedAt: string;
  dueAt: string;
  paidAt?: string;
  subtotal: number;
  taxAmount: number;
  totalAmount: number;
  amountPaid: number;
  amountDue: number;
  currency: string;
  description?: string;
  lineItems: InvoiceLineItem[];
  paymentMethod?: string;
  paymentIntentId?: string;
  metadata: Record<string, any>;
  createdAt: string;
  updatedAt: string;

  // 计算属性
  isPaid: boolean;
  isOverdue: boolean;
  daysOverdue: number;
}

export interface InvoiceLineItem {
  description: string;
  quantity: number;
  unitPrice: number;
  amount: number;
  metadata: Record<string, any>;
}

export interface UsageRecord {
  id: string;
  userId: string;
  subscriptionId?: string;
  apiKeyId?: string;
  usageType: UsageType;
  model?: string;
  endpoint: string;
  method: string;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  requestSize: number;
  responseSize: number;
  responseTimeMs: number;
  statusCode: number;
  cost: number;
  currency: string;
  errorMessage?: string;
  timestamp: string;
  metadata: Record<string, any>;

  // 计算属性
  isSuccessful: boolean;
}

export interface UsageStats {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalTokens: number;
  totalCost: number;
  currency: string;
  averageResponseTime: number;
  p95ResponseTime: number;
  modelUsage: Record<string, number>;
  endpointUsage: Record<string, number>;
  hourlyUsage: Record<string, number>;

  // 计算属性
  successRate: number;
  errorRate: number;
}

export interface QuotaInfo {
  planType: string;
  apiCalls: {
    limit: number;
    used: number;
    remaining: number;
    resetAt: string;
  };
  tokens: {
    limit: number;
    used: number;
    remaining: number;
    resetAt: string;
  };
  storage: {
    limit: number;
    used: number;
    remaining: number;
  };
  rateLimit: {
    requestsPerMinute: number;
    requestsPerDay: number;
  };
  features: string[];
  warnings: QuotaWarning[];
}

export interface QuotaWarning {
  type: QuotaType;
  currentUsage: number;
  limit: number;
  percentageUsed: number;
  message: string;
  severity: 'info' | 'warning' | 'error';
}

export interface QuotaViolation {
  id: string;
  userId: string;
  quotaType: QuotaType;
  currentUsage: number;
  limit: number;
  requestedAmount: number;
  wouldExceedBy: number;
  timestamp: string;
  resolved: boolean;
  resolvedAt?: string;
  resolutionMethod?: string;
}

// API请求/响应类型
export interface CreateSubscriptionRequest {
  planType: PlanType;
  billingCycle: BillingCycle;
  paymentProvider: PaymentProvider;
  paymentMethodId?: string;
}

export interface CreateSubscriptionResponse {
  subscriptionId: string;
  userId: string;
  planType: string;
  billingCycle: string;
  provider: string;
  status: string;
  currentPeriodStart: string;
  currentPeriodEnd: string;
  externalSubscription?: Record<string, any>;
}

export interface CancelSubscriptionRequest {
  atPeriodEnd: boolean;
}

export interface UpgradeSubscriptionRequest {
  newPlanType: PlanType;
}

export interface PaymentIntentRequest {
  amount: number;
  paymentProvider: PaymentProvider;
  paymentMethodId?: string;
  description?: string;
}

export interface PaymentIntentResponse {
  success: boolean;
  paymentIntentId: string;
  clientSecret?: string;
  approvalUrl?: string;
  failureReason?: string;
}

export interface PaymentConfirmRequest {
  paymentIntentId: string;
  paymentMethodId?: string;
}

export interface UsageTrackingRequest {
  usageType: UsageType;
  model?: string;
  inputTokens: number;
  outputTokens: number;
  requestSize: number;
  responseSize: number;
  responseTimeMs: number;
  statusCode: number;
  metadata: Record<string, any>;
}

export interface BillingSummary {
  userId: string;
  currentSubscription: {
    planType: string;
    status: string;
    currentPeriodEnd?: string;
    daysUntilRenewal?: number;
  };
  usageThisMonth: {
    totalRequests: number;
    totalTokens: number;
    totalCost: number;
    successfulRequests: number;
    failedRequests: number;
  };
  quotaStatus: QuotaInfo;
  billingPeriod: {
    start: string;
    end: string;
  };
}

export interface InvoiceGenerateRequest {
  invoiceType: string;
  periodStart?: string;
  periodEnd?: string;
}

// UI状态类型
export interface BillingState {
  // 订阅状态
  subscriptions: Subscription[];
  currentSubscription: Subscription | null;
  availablePlans: PricingPlan[];
  subscriptionLoading: boolean;
  subscriptionError: string | null;

  // 支付状态
  paymentMethods: PaymentMethod[];
  payments: Payment[];
  paymentLoading: boolean;
  paymentError: string | null;

  // 使用量状态
  usageStats: UsageStats | null;
  quotaInfo: QuotaInfo | null;
  usageLoading: boolean;
  usageError: string | null;

  // 发票状态
  invoices: Invoice[];
  invoiceLoading: boolean;
  invoiceError: string | null;

  // 计费摘要
  billingSummary: BillingSummary | null;
  summaryLoading: boolean;
  summaryError: string | null;
}

export interface BillingActions {
  // 订阅操作
  createSubscription: (request: CreateSubscriptionRequest) => Promise<void>;
  cancelSubscription: (subscriptionId: string, atPeriodEnd: boolean) => Promise<void>;
  upgradeSubscription: (subscriptionId: string, newPlanType: PlanType) => Promise<void>;
  getSubscriptions: () => Promise<void>;
  getCurrentSubscription: () => Promise<void>;
  getAvailablePlans: () => Promise<void>;

  // 支付操作
  createPaymentIntent: (request: PaymentIntentRequest) => Promise<PaymentIntentResponse>;
  confirmPayment: (request: PaymentConfirmRequest) => Promise<void>;
  getPaymentMethods: () => Promise<void>;
  getPaymentHistory: () => Promise<void>;

  // 使用量操作
  trackUsage: (request: UsageTrackingRequest) => Promise<void>;
  getUsageStats: (startDate: string, endDate: string, usageType?: UsageType) => Promise<void>;
  getQuotaStatus: () => Promise<void>;

  // 发票操作
  generateInvoice: (request: InvoiceGenerateRequest) => Promise<void>;
  getInvoices: () => Promise<void>;
  downloadInvoice: (invoiceId: string) => Promise<Blob>;

  // 摘要操作
  getBillingSummary: () => Promise<void>;

  // 清理操作
  clearErrors: () => void;
  resetState: () => void;
}

// 组件Props类型
export interface PlanCardProps {
  plan: PricingPlan;
  currentPlan?: PlanType;
  onSelectPlan: (plan: PricingPlan) => void;
  loading?: boolean;
  disabled?: boolean;
}

export interface SubscriptionCardProps {
  subscription: Subscription;
  onCancel?: () => void;
  onUpgrade?: () => void;
  onManage?: () => void;
}

export interface UsageChartProps {
  data: Array<{
    date: string;
    requests: number;
    tokens: number;
    cost: number;
  }>;
  type: 'requests' | 'tokens' | 'cost';
  height?: number;
}

export interface QuotaIndicatorProps {
  quota: QuotaInfo;
  type: QuotaType;
  showDetails?: boolean;
}

export interface PaymentMethodFormProps {
  onSuccess?: (paymentMethod: PaymentMethod) => void;
  onCancel?: () => void;
  provider: PaymentProvider;
}

export interface InvoiceListItemProps {
  invoice: Invoice;
  onView?: (invoice: Invoice) => void;
  onDownload?: (invoice: Invoice) => void;
}

export interface BillingNotificationProps {
  type: 'success' | 'warning' | 'error' | 'info';
  title: string;
  message: string;
  actions?: Array<{
    label: string;
    action: () => void;
    variant?: 'primary' | 'secondary';
  }>;
  onDismiss?: () => void;
}

// 工具类型
export type BillingError = {
  code: string;
  message: string;
  details?: Record<string, any>;
};

export type BillingLoadingState = {
  subscriptions: boolean;
  payments: boolean;
  usage: boolean;
  invoices: boolean;
  summary: boolean;
};

export type BillingFilter = {
  status?: SubscriptionStatus | PaymentStatus | InvoiceStatus;
  dateRange?: {
    start: string;
    end: string;
  };
  planType?: PlanType;
  provider?: PaymentProvider;
};

export type BillingSort = {
  field: string;
  direction: 'asc' | 'desc';
};

// 表单验证类型
export interface PaymentFormValues {
  cardNumber: string;
  expiryDate: string;
  cvc: string;
  cardholderName: string;
  saveCard: boolean;
  setAsDefault: boolean;
}

export interface BillingSettingsValues {
  emailNotifications: boolean;
  invoiceEmail: string;
  autoRenewal: boolean;
  paymentMethod: string;
  billingAddress: {
    line1: string;
    line2?: string;
    city: string;
    state: string;
    postalCode: string;
    country: string;
  };
}

// 响应式类型
export interface BillingBreakpoints {
  mobile: '640px';
  tablet: '768px';
  desktop: '1024px';
  wide: '1280px';
}

// 动画类型
export interface BillingAnimations {
  fadeIn: {
    initial: { opacity: 0 };
    animate: { opacity: 1 };
    exit: { opacity: 0 };
  };
  slideUp: {
    initial: { y: 20, opacity: 0 };
    animate: { y: 0, opacity: 1 };
    exit: { y: -20, opacity: 0 };
  };
  scale: {
    initial: { scale: 0.95, opacity: 0 };
    animate: { scale: 1, opacity: 1 };
    exit: { scale: 1.05, opacity: 0 };
  };
}

// 导出所有类型
export type {
  // 核心类型
  PlanType,
  BillingCycle,
  PaymentProvider,
  PaymentStatus,
  SubscriptionStatus,
  InvoiceStatus,
  UsageType,
  QuotaType,

  // 数据类型
  Currency,
  PricingPlan,
  Subscription,
  PaymentMethod,
  Payment,
  Invoice,
  InvoiceLineItem,
  UsageRecord,
  UsageStats,
  QuotaInfo,
  QuotaWarning,
  QuotaViolation,

  // API类型
  CreateSubscriptionRequest,
  CreateSubscriptionResponse,
  CancelSubscriptionRequest,
  UpgradeSubscriptionRequest,
  PaymentIntentRequest,
  PaymentIntentResponse,
  PaymentConfirmRequest,
  UsageTrackingRequest,
  BillingSummary,
  InvoiceGenerateRequest,

  // 状态类型
  BillingState,
  BillingActions,
  BillingError,
  BillingLoadingState,
  BillingFilter,
  BillingSort,

  // 组件类型
  PlanCardProps,
  SubscriptionCardProps,
  UsageChartProps,
  QuotaIndicatorProps,
  PaymentMethodFormProps,
  InvoiceListItemProps,
  BillingNotificationProps,

  // 表单类型
  PaymentFormValues,
  BillingSettingsValues,

  // 其他类型
  BillingBreakpoints,
  BillingAnimations
};