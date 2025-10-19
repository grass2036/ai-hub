'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

// 类型定义
interface Invoice {
  id: string;
  invoice_number: string;
  amount: number;
  status: 'pending' | 'paid' | 'overdue' | 'cancelled';
  billing_period: {
    start: string;
    end: string;
  };
  due_date: string;
  created_at: string;
  paid_at?: string;
  payment_method?: string;
  items: InvoiceItem[];
}

interface InvoiceItem {
  description: string;
  quantity: number;
  unit_price: number;
  total: number;
}

interface PaymentMethod {
  id: string;
  type: 'credit_card' | 'bank_transfer' | 'paypal';
  details: {
    last4?: string;
    brand?: string;
    bank_name?: string;
    email?: string;
  };
  is_default: boolean;
  created_at: string;
}

interface BillingOverview {
  current_month_cost: number;
  last_month_cost: number;
  total_unpaid: number;
  upcoming_payment: number;
  payment_method: string;
  next_billing_date: string;
  credit_balance: number;
  subscription_status: string;
}

export default function DeveloperBilling() {
  const router = useRouter();
  const [billingOverview, setBillingOverview] = useState<BillingOverview | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'overview' | 'invoices' | 'payment-methods'>('overview');
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('developer_access_token');

      if (!token) {
        router.push('/developer/login');
        return;
      }

      try {
        // 并行获取所有数据
        const [overviewRes, invoicesRes, paymentMethodsRes] = await Promise.all([
          fetch('/api/v1/developer/usage/billing/overview', {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch(`/api/v1/developer/usage/billing/invoices?page=${currentPage}&limit=20`, {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch('/api/v1/developer/usage/billing/payment-methods', {
            headers: { 'Authorization': `Bearer ${token}` }
          })
        ]);

        if (overviewRes.ok) {
          const overviewResult = await overviewRes.json();
          setBillingOverview(overviewResult.data);
        }

        if (invoicesRes.ok) {
          const invoicesResult = await invoicesRes.json();
          setInvoices(invoicesResult.data.invoices || []);
        }

        if (paymentMethodsRes.ok) {
          const paymentMethodsResult = await paymentMethodsRes.json();
          setPaymentMethods(paymentMethodsResult.data || []);
        }

      } catch (err) {
        setError('加载数据失败');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [router, currentPage]);

  const handlePayInvoice = async (invoiceId: string, paymentMethodId: string) => {
    const token = localStorage.getItem('developer_access_token');
    if (!token) return;

    try {
      const response = await fetch(`/api/v1/developer/usage/billing/invoices/${invoiceId}/pay`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ payment_method_id: paymentMethodId })
      });

      if (response.ok) {
        // 刷新数据
        window.location.reload();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || '支付失败');
      }
    } catch (err) {
      setError('支付失败');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'overdue':
        return 'bg-red-100 text-red-800';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'paid':
        return '已支付';
      case 'pending':
        return '待支付';
      case 'overdue':
        return '逾期';
      case 'cancelled':
        return '已取消';
      default:
        return status;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">加载失败</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航栏 */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link href="/developer" className="text-blue-600 hover:text-blue-800">
                ← 返回控制台
              </Link>
              <h1 className="ml-4 text-xl font-bold text-gray-900">
                账单管理
              </h1>
            </div>
          </div>
        </div>
      </nav>

      {/* 主要内容 */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* 标签页导航 */}
        <div className="bg-white shadow rounded-lg mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8 px-6">
              {[
                { id: 'overview', label: '账单概览', icon: '📊' },
                { id: 'invoices', label: '发票记录', icon: '🧾' },
                { id: 'payment-methods', label: '支付方式', icon: '💳' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* 账单概览标签页 */}
        {activeTab === 'overview' && billingOverview && (
          <div className="space-y-6">
            {/* 统计卡片 */}
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                      </div>
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">本月费用</dt>
                        <dd className="text-lg font-medium text-gray-900">
                          ${billingOverview.current_month_cost.toFixed(2)}
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">上月费用</dt>
                        <dd className="text-lg font-medium text-gray-900">
                          ${billingOverview.last_month_cost.toFixed(2)}
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">待支付金额</dt>
                        <dd className="text-lg font-medium text-gray-900">
                          ${billingOverview.total_unpaid.toFixed(2)}
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                        </svg>
                      </div>
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">信用余额</dt>
                        <dd className="text-lg font-medium text-gray-900">
                          ${billingOverview.credit_balance.toFixed(2)}
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 账单详情 */}
            <div className="bg-white shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-6">
                  账单详情
                </h3>
                <div className="space-y-4">
                  <div className="flex justify-between items-center py-3 border-b">
                    <span className="text-sm font-medium text-gray-600">订阅状态</span>
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      billingOverview.subscription_status === 'active' ? 'bg-green-100 text-green-800' :
                      billingOverview.subscription_status === 'trial' ? 'bg-blue-100 text-blue-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {billingOverview.subscription_status === 'active' ? '活跃' :
                       billingOverview.subscription_status === 'trial' ? '试用' :
                       '未激活'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-3 border-b">
                    <span className="text-sm font-medium text-gray-600">下次扣款日期</span>
                    <span className="text-sm text-gray-900">
                      {billingOverview.next_billing_date ? new Date(billingOverview.next_billing_date).toLocaleDateString() : '未设置'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-3 border-b">
                    <span className="text-sm font-medium text-gray-600">预计下次扣款</span>
                    <span className="text-sm font-medium text-gray-900">
                      ${billingOverview.upcoming_payment.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-3">
                    <span className="text-sm font-medium text-gray-600">当前支付方式</span>
                    <span className="text-sm text-gray-900">
                      {billingOverview.payment_method || '未设置'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 发票记录标签页 */}
        {activeTab === 'invoices' && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-6">
                发票记录
              </h3>
              {invoices.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          发票编号
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          账单周期
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          金额
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          状态
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          到期日期
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          操作
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {invoices.map((invoice) => (
                        <tr key={invoice.id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {invoice.invoice_number}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {new Date(invoice.billing_period.start).toLocaleDateString()} - {new Date(invoice.billing_period.end).toLocaleDateString()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            ${invoice.amount.toFixed(2)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(invoice.status)}`}>
                              {getStatusText(invoice.status)}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {new Date(invoice.due_date).toLocaleDateString()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <button
                              onClick={() => setSelectedInvoice(invoice)}
                              className="text-blue-600 hover:text-blue-900 mr-3"
                            >
                              查看
                            </button>
                            {invoice.status === 'pending' && paymentMethods.length > 0 && (
                              <button
                                onClick={() => {
                                  const defaultMethod = paymentMethods.find(m => m.is_default) || paymentMethods[0];
                                  if (defaultMethod) {
                                    handlePayInvoice(invoice.id, defaultMethod.id);
                                  }
                                }}
                                className="text-green-600 hover:text-green-900"
                              >
                                支付
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">暂无发票记录</p>
              )}

              {/* 分页 */}
              {invoices.length > 0 && (
                <div className="mt-4 flex justify-center">
                  <div className="flex space-x-2">
                    <button
                      onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                      disabled={currentPage === 1}
                      className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
                    >
                      上一页
                    </button>
                    <span className="px-3 py-1 text-gray-700">
                      第 {currentPage} 页
                    </span>
                    <button
                      onClick={() => setCurrentPage(currentPage + 1)}
                      className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                    >
                      下一页
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 支付方式标签页 */}
        {activeTab === 'payment-methods' && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900">
                  支付方式
                </h3>
                <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm">
                  添加支付方式
                </button>
              </div>
              {paymentMethods.length > 0 ? (
                <div className="space-y-4">
                  {paymentMethods.map((method) => (
                    <div key={method.id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className="text-2xl">
                            {method.type === 'credit_card' ? '💳' :
                             method.type === 'bank_transfer' ? '🏦' : '📧'}
                          </div>
                          <div>
                            <div className="font-medium text-gray-900">
                              {method.type === 'credit_card' ? '信用卡' :
                               method.type === 'bank_transfer' ? '银行转账' : 'PayPal'}
                            </div>
                            <div className="text-sm text-gray-500">
                              {method.type === 'credit_card' && method.details.last4 &&
                                `**** **** **** ${method.details.last4}`}
                              {method.type === 'bank_transfer' && method.details.bank_name &&
                                method.details.bank_name}
                              {method.type === 'paypal' && method.details.email &&
                                method.details.email}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          {method.is_default && (
                            <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                              默认
                            </span>
                          )}
                          <button className="text-blue-600 hover:text-blue-900 text-sm">
                            编辑
                          </button>
                          <button className="text-red-600 hover:text-red-900 text-sm">
                            删除
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <div className="text-gray-400 text-4xl mb-4">💳</div>
                  <p className="text-gray-500 mb-4">您还没有添加任何支付方式</p>
                  <button className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700">
                    添加支付方式
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* 发票详情模态框 */}
      {selectedInvoice && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full mx-4 max-h-screen overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-start mb-6">
                <h3 className="text-xl font-bold text-gray-900">
                  发票详情 - {selectedInvoice.invoice_number}
                </h3>
                <button
                  onClick={() => setSelectedInvoice(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">发票编号</p>
                    <p className="font-medium">{selectedInvoice.invoice_number}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">状态</p>
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(selectedInvoice.status)}`}>
                      {getStatusText(selectedInvoice.status)}
                    </span>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">账单周期</p>
                    <p className="font-medium">
                      {new Date(selectedInvoice.billing_period.start).toLocaleDateString()} - {new Date(selectedInvoice.billing_period.end).toLocaleDateString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">到期日期</p>
                    <p className="font-medium">{new Date(selectedInvoice.due_date).toLocaleDateString()}</p>
                  </div>
                </div>

                <div>
                  <p className="text-sm font-medium text-gray-900 mb-3">费用明细</p>
                  <div className="border rounded-lg overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            描述
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            数量
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            单价
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            小计
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {selectedInvoice.items.map((item, index) => (
                          <tr key={index}>
                            <td className="px-4 py-3 text-sm text-gray-900">{item.description}</td>
                            <td className="px-4 py-3 text-sm text-gray-900">{item.quantity}</td>
                            <td className="px-4 py-3 text-sm text-gray-900">${item.unit_price.toFixed(2)}</td>
                            <td className="px-4 py-3 text-sm font-medium text-gray-900">${item.total.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot className="bg-gray-50">
                        <tr>
                          <td colSpan={3} className="px-4 py-3 text-sm font-medium text-gray-900">
                            总计
                          </td>
                          <td className="px-4 py-3 text-lg font-bold text-gray-900">
                            ${selectedInvoice.amount.toFixed(2)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>

                {selectedInvoice.paid_at && (
                  <div>
                    <p className="text-sm text-gray-600">支付时间</p>
                    <p className="font-medium">{new Date(selectedInvoice.paid_at).toLocaleString()}</p>
                  </div>
                )}
              </div>

              <div className="mt-6 flex justify-end space-x-3">
                <button
                  onClick={() => setSelectedInvoice(null)}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  关闭
                </button>
                {selectedInvoice.status === 'pending' && (
                  <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
                    下载发票
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}