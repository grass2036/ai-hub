/**
 * 发票管理页面
 *
 * 显示发票列表、搜索、过滤和下载功能。
 */

'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';

// 组件导入
import { BillingLayout, BillingHeader } from '@/components/billing/billing-layout';
import { InvoiceList } from '@/components/billing/invoice-list';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// Hooks导入
import { useInvoiceManagement } from '@/store/billing-store';

// 图标导入
import {
  DocumentTextIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowDownTrayIcon,
  PlusIcon,
  CalendarIcon,
  CurrencyDollarIcon,
} from '@heroicons/react/24/outline';

const InvoicesManagement: React.FC = () => {
  const { invoices, loading, error, actions } = useInvoiceManagement();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [dateFilter, setDateFilter] = useState('all');

  useEffect(() => {
    const fetchInvoices = async () => {
      try {
        await actions.getInvoices();
      } catch (error) {
        console.error('Failed to fetch invoices:', error);
      }
    };

    fetchInvoices();
  }, [actions]);

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const filteredInvoices = invoices?.filter(invoice => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      if (!invoice.invoiceNumber.toLowerCase().includes(query) &&
          !invoice.description?.toLowerCase().includes(query)) {
        return false;
      }
    }

    // Status filter
    if (statusFilter !== 'all' && invoice.status !== statusFilter) {
      return false;
    }

    // Date filter
    if (dateFilter !== 'all') {
      const invoiceDate = new Date(invoice.issuedAt);
      const now = new Date();

      switch (dateFilter) {
        case 'this_month':
          const thisMonth = invoiceDate.getMonth() === now.getMonth() &&
                           invoiceDate.getFullYear() === now.getFullYear();
          if (!thisMonth) return false;
          break;
        case 'last_month':
          const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1);
          if (invoiceDate.getMonth() !== lastMonth.getMonth() ||
              invoiceDate.getFullYear() !== lastMonth.getFullYear()) {
            return false;
          }
          break;
        case 'this_year':
          if (invoiceDate.getFullYear() !== now.getFullYear()) return false;
          break;
      }
    }

    return true;
  }) || [];

  const getInvoiceStats = () => {
    if (!invoices || invoices.length === 0) {
      return {
        total: 0,
        paid: 0,
        pending: 0,
        overdue: 0,
        totalAmount: 0,
      };
    }

    const stats = invoices.reduce((acc, invoice) => {
      acc.total++;
      acc.totalAmount += invoice.totalAmount;

      switch (invoice.status) {
        case 'paid':
          acc.paid++;
          break;
        case 'pending':
          acc.pending++;
          break;
        case 'overdue':
          acc.overdue++;
          break;
      }

      return acc;
    }, {
      total: 0,
      paid: 0,
      pending: 0,
      overdue: 0,
      totalAmount: 0,
    });

    return stats;
  };

  const stats = getInvoiceStats();

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

  if (loading) {
    return (
      <BillingLayout>
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="h-96 bg-gray-200 rounded"></div>
        </div>
      </BillingLayout>
    );
  }

  return (
    <BillingLayout>
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Page Header */}
        <BillingHeader
          title="Invoices"
          description="View, download, and manage your billing invoices"
          actions={
            <div className="flex items-center gap-3">
              <Button variant="outline" onClick={() => actions.getInvoices()}>
                <ArrowDownTrayIcon className="w-4 h-4 mr-2" />
                Export All
              </Button>
              <Button asChild>
                <Link href="/billing/payments/methods">
                  <PlusIcon className="w-4 h-4 mr-2" />
                  Add Payment Method
                </Link>
              </Button>
            </div>
          }
        />

        {/* Stats Cards */}
        <motion.div
          variants={itemVariants}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
        >
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Invoices</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{stats.total}</p>
                </div>
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <DocumentTextIcon className="w-6 h-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Paid</p>
                  <p className="text-2xl font-bold text-green-600 mt-1">{stats.paid}</p>
                </div>
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <div className="w-6 h-6 bg-green-600 rounded-full"></div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Pending</p>
                  <p className="text-2xl font-bold text-yellow-600 mt-1">{stats.pending}</p>
                </div>
                <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                  <div className="w-6 h-6 bg-yellow-600 rounded-full"></div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Amount</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {formatCurrency(stats.totalAmount)}
                  </p>
                </div>
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                  <CurrencyDollarIcon className="w-6 h-6 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Filters and Search */}
        <motion.div variants={itemVariants} className="mb-6">
          <Card>
            <CardContent className="p-4">
              <div className="flex flex-col lg:flex-row gap-4">
                {/* Search */}
                <div className="flex-1">
                  <div className="relative">
                    <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      placeholder="Search invoices..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>

                {/* Status Filter */}
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-40">
                    <FunnelIcon className="w-4 h-4 mr-2" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="paid">Paid</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="overdue">Overdue</SelectItem>
                    <SelectItem value="draft">Draft</SelectItem>
                  </SelectContent>
                </Select>

                {/* Date Filter */}
                <Select value={dateFilter} onValueChange={setDateFilter}>
                  <SelectTrigger className="w-40">
                    <CalendarIcon className="w-4 h-4 mr-2" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Time</SelectItem>
                    <SelectItem value="this_month">This Month</SelectItem>
                    <SelectItem value="last_month">Last Month</SelectItem>
                    <SelectItem value="this_year">This Year</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Active Filters */}
              {(searchQuery || statusFilter !== 'all' || dateFilter !== 'all') && (
                <div className="mt-4 flex items-center gap-2">
                  <span className="text-sm text-gray-600">Active filters:</span>
                  {searchQuery && (
                    <Badge variant="secondary" className="gap-1">
                      Search: {searchQuery}
                      <button
                        onClick={() => setSearchQuery('')}
                        className="hover:bg-gray-200 rounded-full p-0.5"
                      >
                        ×
                      </button>
                    </Badge>
                  )}
                  {statusFilter !== 'all' && (
                    <Badge variant="secondary" className="gap-1">
                      Status: {statusFilter}
                      <button
                        onClick={() => setStatusFilter('all')}
                        className="hover:bg-gray-200 rounded-full p-0.5"
                      >
                        ×
                      </button>
                    </Badge>
                  )}
                  {dateFilter !== 'all' && (
                    <Badge variant="secondary" className="gap-1">
                      Date: {dateFilter.replace('_', ' ')}
                      <button
                        onClick={() => setDateFilter('all')}
                        className="hover:bg-gray-200 rounded-full p-0.5"
                      >
                        ×
                      </button>
                    </Badge>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setSearchQuery('');
                      setStatusFilter('all');
                      setDateFilter('all');
                    }}
                  >
                    Clear all
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Invoice List */}
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Invoices ({filteredInvoices.length})</span>
                {filteredInvoices.length !== invoices?.length && (
                  <span className="text-sm font-normal text-gray-600">
                    Showing filtered results
                  </span>
                )}
              </CardTitle>
              <CardDescription>
                Your billing history and invoice documents
              </CardDescription>
            </CardHeader>
            <CardContent>
              <InvoiceList
                invoices={filteredInvoices}
                loading={loading}
                onDownloadInvoice={actions.downloadInvoice}
              />
            </CardContent>
          </Card>
        </motion.div>

        {/* Quick Actions */}
        <motion.div variants={itemVariants} className="mt-8">
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
              <CardDescription>
                Common tasks related to your invoices
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Button variant="outline" className="justify-start h-auto p-4" asChild>
                  <Link href="/billing/payments/methods">
                    <CurrencyDollarIcon className="w-5 h-5 mr-3" />
                    <div className="text-left">
                      <div className="font-medium">Payment Methods</div>
                      <div className="text-sm text-gray-600">Manage your payment options</div>
                    </div>
                  </Link>
                </Button>

                <Button variant="outline" className="justify-start h-auto p-4" asChild>
                  <Link href="/billing/subscription">
                    <DocumentTextIcon className="w-5 h-5 mr-3" />
                    <div className="text-left">
                      <div className="font-medium">Subscription</div>
                      <div className="text-sm text-gray-600">View and manage your plan</div>
                    </div>
                  </Link>
                </Button>

                <Button variant="outline" className="justify-start h-auto p-4" asChild>
                  <Link href="/billing/settings">
                    <FunnelIcon className="w-5 h-5 mr-3" />
                    <div className="text-left">
                      <div className="font-medium">Billing Settings</div>
                      <div className="text-sm text-gray-600">Configure preferences</div>
                    </div>
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>
    </BillingLayout>
  );
};

export default InvoicesManagement;