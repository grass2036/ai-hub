/**
 * 发票管理组件
 *
 * 提供发票列表、详情查看、下载等功能。
 */

'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  DocumentArrowDownIcon,
  DocumentTextIcon,
  EyeIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
  CalendarIcon,
  CurrencyDollarIcon,
} from '@heroicons/react/24/outline';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
} from '@heroicons/react/24/solid';

import { Invoice, InvoiceStatus } from '@/types/billing';
import { useInvoiceManagement } from '@/store/billing-store';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { toast } from 'react-hot-toast';

interface InvoiceManagementProps {
  className?: string;
}

const invoiceStatusConfig = {
  [InvoiceStatus.DRAFT]: {
    label: 'Draft',
    color: 'gray',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-700',
    icon: DocumentTextIcon,
  },
  [InvoiceStatus.PENDING]: {
    label: 'Pending',
    color: 'yellow',
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-700',
    icon: ClockIcon,
  },
  [InvoiceStatus.PAID]: {
    label: 'Paid',
    color: 'green',
    bgColor: 'bg-green-50',
    textColor: 'text-green-700',
    icon: CheckCircleIcon,
  },
  [InvoiceStatus.PARTIALLY_PAID]: {
    label: 'Partially Paid',
    color: 'blue',
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-700',
    icon: ClockIcon,
  },
  [InvoiceStatus.OVERDUE]: {
    label: 'Overdue',
    color: 'red',
    bgColor: 'bg-red-50',
    textColor: 'text-red-700',
    icon: ExclamationTriangleIcon,
  },
  [InvoiceStatus.VOID]: {
    label: 'Void',
    color: 'gray',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-700',
    icon: XMarkIcon,
  },
  [InvoiceStatus.REFUNDED]: {
    label: 'Refunded',
    color: 'purple',
    bgColor: 'bg-purple-50',
    textColor: 'text-purple-700',
    icon: DocumentTextIcon,
  },
};

const InvoiceListItem: React.FC<{
  invoice: Invoice;
  onView: (invoice: Invoice) => void;
  onDownload: (invoice: Invoice) => void;
}> = ({ invoice, onView, onDownload }) => {
  const statusConfig = invoiceStatusConfig[invoice.status];
  const StatusIcon = statusConfig.icon;

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const isOverdue = invoice.isOverdue;
  const daysOverdue = invoice.daysOverdue;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h4 className="font-semibold text-gray-900">
              {invoice.invoiceNumber}
            </h4>
            <Badge className={cn(
              'flex items-center gap-1',
              statusConfig.bgColor,
              statusConfig.textColor,
              'border-0'
            )}>
              <StatusIcon className="w-3 h-3" />
              {statusConfig.label}
            </Badge>
            {isOverdue && (
              <Badge variant="destructive" className="text-xs">
                {daysOverdue} days overdue
              </Badge>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
            <div>
              <div className="text-gray-600">Issue Date</div>
              <div className="font-medium text-gray-900">
                {formatDate(invoice.issuedAt)}
              </div>
            </div>

            <div>
              <div className="text-gray-600">Due Date</div>
              <div className={cn(
                'font-medium',
                isOverdue ? 'text-red-600' : 'text-gray-900'
              )}>
                {formatDate(invoice.dueAt)}
              </div>
            </div>

            <div>
              <div className="text-gray-600">Amount</div>
              <div className="font-medium text-gray-900">
                {formatCurrency(invoice.totalAmount, invoice.currency)}
              </div>
            </div>

            <div>
              <div className="text-gray-600">Amount Paid</div>
              <div className="font-medium text-gray-900">
                {formatCurrency(invoice.amountPaid, invoice.currency)}
              </div>
            </div>
          </div>

          {invoice.description && (
            <div className="mt-2 text-sm text-gray-600">
              {invoice.description}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 ml-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onView(invoice)}
            className="flex items-center gap-2"
          >
            <EyeIcon className="w-4 h-4" />
            View
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => onDownload(invoice)}
            className="flex items-center gap-2"
          >
            <DocumentArrowDownIcon className="w-4 h-4" />
            PDF
          </Button>
        </div>
      </div>
    </motion.div>
  );
};

const InvoiceDetail: React.FC<{
  invoice: Invoice;
  onClose: () => void;
  onDownload: (invoice: Invoice) => void;
}> = ({ invoice, onClose, onDownload }) => {
  const statusConfig = invoiceStatusConfig[invoice.status];
  const StatusIcon = statusConfig.icon;

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Invoice {invoice.invoiceNumber}
          </h3>
          <p className="text-sm text-gray-600">
            Issued on {formatDate(invoice.issuedAt)}
          </p>
        </div>

        <Badge className={cn(
          'flex items-center gap-1',
          statusConfig.bgColor,
          statusConfig.textColor,
          'border-0'
        )}>
          <StatusIcon className="w-4 h-4" />
          {statusConfig.label}
        </Badge>
      </div>

      {/* Invoice Summary */}
      <Card className="p-6">
        <h4 className="font-medium text-gray-900 mb-4">Invoice Summary</h4>

        <div className="space-y-3">
          <div className="flex justify-between">
            <span className="text-gray-600">Invoice Number:</span>
            <span className="font-medium text-gray-900">{invoice.invoiceNumber}</span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-600">Issue Date:</span>
            <span className="font-medium text-gray-900">{formatDate(invoice.issuedAt)}</span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-600">Due Date:</span>
            <span className={cn(
              'font-medium',
              invoice.isOverdue ? 'text-red-600' : 'text-gray-900'
            )}>
              {formatDate(invoice.dueAt)}
            </span>
          </div>

          {invoice.paidAt && (
            <div className="flex justify-between">
              <span className="text-gray-600">Paid Date:</span>
              <span className="font-medium text-gray-900">{formatDate(invoice.paidAt)}</span>
            </div>
          )}

          <div className="flex justify-between">
            <span className="text-gray-600">Status:</span>
            <span className="font-medium text-gray-900">{statusConfig.label}</span>
          </div>

          <Separator />

          <div className="flex justify-between">
            <span className="text-gray-600">Subtotal:</span>
            <span className="font-medium text-gray-900">
              {formatCurrency(invoice.subtotal, invoice.currency)}
            </span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-600">Tax Amount:</span>
            <span className="font-medium text-gray-900">
              {formatCurrency(invoice.taxAmount, invoice.currency)}
            </span>
          </div>

          <div className="flex justify-between font-semibold text-lg">
            <span>Total Amount:</span>
            <span className="text-gray-900">
              {formatCurrency(invoice.totalAmount, invoice.currency)}
            </span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-600">Amount Paid:</span>
            <span className="font-medium text-green-600">
              {formatCurrency(invoice.amountPaid, invoice.currency)}
            </span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-600">Amount Due:</span>
            <span className={cn(
              'font-semibold text-lg',
              invoice.amountDue > 0 ? 'text-red-600' : 'text-green-600'
            )}>
              {formatCurrency(invoice.amountDue, invoice.currency)}
            </span>
          </div>
        </div>
      </Card>

      {/* Line Items */}
      <Card className="p-6">
        <h4 className="font-medium text-gray-900 mb-4">Invoice Items</h4>

        <div className="space-y-3">
          {invoice.lineItems.map((item, index) => (
            <div key={index} className="flex justify-between items-start">
              <div className="flex-1">
                <div className="font-medium text-gray-900">
                  {item.description}
                </div>
                <div className="text-sm text-gray-600">
                  Quantity: {item.quantity} × {formatCurrency(item.unitPrice, invoice.currency)}
                </div>
              </div>
              <div className="font-medium text-gray-900 ml-4">
                {formatCurrency(item.amount, invoice.currency)}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Actions */}
      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={onClose}>
          Close
        </Button>
        <Button
          onClick={() => onDownload(invoice)}
          className="flex items-center gap-2"
        >
          <DocumentArrowDownIcon className="w-4 h-4" />
          Download PDF
        </Button>
      </div>
    </div>
  );
};

export const InvoiceManagement: React.FC<InvoiceManagementProps> = ({ className }) => {
  const { invoices, loading, actions } = useInvoiceManagement();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  // Load invoices on mount
  useEffect(() => {
    actions.getInvoices();
  }, [actions]);

  // Filter invoices
  const filteredInvoices = invoices.filter(invoice => {
    const matchesSearch = searchTerm === '' ||
      invoice.invoiceNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      invoice.description?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = statusFilter === 'all' || invoice.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const handleViewInvoice = (invoice: Invoice) => {
    setSelectedInvoice(invoice);
    setShowDetail(true);
  };

  const handleDownloadInvoice = async (invoice: Invoice) => {
    setDownloadingId(invoice.id);
    try {
      const pdfBlob = await actions.downloadInvoice(invoice.id);

      // Create download link
      const url = window.URL.createObjectURL(pdfBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `invoice-${invoice.invoiceNumber}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success('Invoice downloaded successfully');
    } catch (error) {
      toast.error('Failed to download invoice');
      console.error('Download error:', error);
    } finally {
      setDownloadingId(null);
    }
  };

  const handleCloseDetail = () => {
    setShowDetail(false);
    setSelectedInvoice(null);
  };

  if (loading && invoices.length === 0) {
    return (
      <div className={cn('space-y-6', className)}>
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">Invoices</h2>
        </div>

        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="p-4">
              <div className="animate-pulse">
                <div className="flex items-center gap-3 mb-3">
                  <div className="h-4 bg-gray-200 rounded w-24"></div>
                  <div className="h-4 bg-gray-200 rounded w-16"></div>
                </div>
                <div className="grid grid-cols-4 gap-4">
                  <div className="h-3 bg-gray-200 rounded"></div>
                  <div className="h-3 bg-gray-200 rounded"></div>
                  <div className="h-3 bg-gray-200 rounded"></div>
                  <div className="h-3 bg-gray-200 rounded"></div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Invoices</h2>
          <p className="text-gray-600">
            Manage and download your billing invoices
          </p>
        </div>

        <Button onClick={() => actions.getInvoices()} variant="outline">
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search invoices..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {/* Status Filter */}
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value={InvoiceStatus.DRAFT}>Draft</SelectItem>
              <SelectItem value={InvoiceStatus.PENDING}>Pending</SelectItem>
              <SelectItem value={InvoiceStatus.PAID}>Paid</SelectItem>
              <SelectItem value={InvoiceStatus.PARTIALLY_PAID}>Partially Paid</SelectItem>
              <SelectItem value={InvoiceStatus.OVERDUE}>Overdue</SelectItem>
              <SelectItem value={InvoiceStatus.VOID}>Void</SelectItem>
              <SelectItem value={InvoiceStatus.REFUNDED}>Refunded</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* Invoice List */}
      {filteredInvoices.length === 0 ? (
        <Card className="p-12 text-center">
          <DocumentTextIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {searchTerm || statusFilter !== 'all' ? 'No invoices found' : 'No invoices yet'}
          </h3>
          <p className="text-gray-600 mb-4">
            {searchTerm || statusFilter !== 'all'
              ? 'Try adjusting your search or filters'
              : 'Your invoices will appear here once they are generated'
            }
          </p>
          {(searchTerm || statusFilter !== 'all') && (
            <Button
              variant="outline"
              onClick={() => {
                setSearchTerm('');
                setStatusFilter('all');
              }}
            >
              Clear Filters
            </Button>
          )}
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredInvoices.map((invoice) => (
            <InvoiceListItem
              key={invoice.id}
              invoice={invoice}
              onView={handleViewInvoice}
              onDownload={handleDownloadInvoice}
            />
          ))}
        </div>
      )}

      {/* Invoice Detail Modal */}
      <Dialog open={showDetail} onOpenChange={setShowDetail}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Invoice Details</DialogTitle>
          </DialogHeader>

          {selectedInvoice && (
            <InvoiceDetail
              invoice={selectedInvoice}
              onClose={handleCloseDetail}
              onDownload={handleDownloadInvoice}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default InvoiceManagement;