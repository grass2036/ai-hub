/**
 * 发票管理页面
 *
 * 提供发票列表查看、下载、搜索等功能。
 */

'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  DocumentTextIcon,
  DocumentArrowDownIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  CalendarIcon,
  CurrencyDollarIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';

import { BillingLayout, BillingHeader } from '@/components/billing/billing-layout';
import { InvoiceManagement } from '@/components/billing/invoice-management';

export default function InvoicesPage() {
  return (
    <BillingLayout>
      <div className="space-y-6">
        <BillingHeader
          title="Invoices & Billing"
          description="View and download your billing invoices and payment history"
          actions={
            <Button onClick={() => window.location.href = '/billing/settings'}>
              <DocumentTextIcon className="w-4 h-4 mr-2" />
              Billing Settings
            </Button>
          }
          breadcrumb={[
            { name: 'Billing', href: '/billing' },
            { name: 'Invoices' },
          ]}
        />

        <InvoiceManagement />
      </div>
    </BillingLayout>
  );
}