/**
 * 发票列表组件
 *
 * 显示发票表格，支持查看、下载等操作。
 */

'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';

// 类型导入
import { Invoice, InvoiceListItemProps } from '@/types/billing';

// UI组件导入
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Pagination, PaginationContent, PaginationEllipsis, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from '@/components/ui/pagination';

// 图标导入
import {
  DocumentTextIcon,
  ArrowDownTrayIcon,
  EyeIcon,
  EllipsisVerticalIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

interface InvoiceListProps {
  invoices: Invoice[];
  loading?: boolean;
  onDownloadInvoice?: (invoiceId: string) => Promise<void>;
}

const InvoiceList: React.FC<InvoiceListProps> = ({
  invoices,
  loading = false,
  onDownloadInvoice,
}) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [downloadingInvoiceId, setDownloadingInvoiceId] = useState<string | null>(null);

  const itemsPerPage = 10;
  const totalPages = Math.ceil(invoices.length / itemsPerPage);

  const paginatedInvoices = invoices.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

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

  const handleDownloadInvoice = async (invoiceId: string) => {
    if (!onDownloadInvoice) return;

    setDownloadingInvoiceId(invoiceId);
    try {
      await onDownloadInvoice(invoiceId);
    } catch (error) {
      console.error('Failed to download invoice:', error);
    } finally {
      setDownloadingInvoiceId(null);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'paid':
        return <CheckCircleIcon className="w-4 h-4 text-green-600" />;
      case 'pending':
        return <ClockIcon className="w-4 h-4 text-yellow-600" />;
      case 'overdue':
        return <ExclamationTriangleIcon className="w-4 h-4 text-red-600" />;
      case 'cancelled':
        return <XCircleIcon className="w-4 h-4 text-gray-600" />;
      default:
        return <ClockIcon className="w-4 h-4 text-gray-600" />;
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

  const getDaysOverdue = (dueDate: string) => {
    const now = new Date();
    const due = new Date(dueDate);
    const diffTime = now.getTime() - due.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays > 0 ? diffDays : 0;
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.05,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        type: 'spring',
        damping: 20,
        stiffness: 100,
      },
    },
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="h-16 bg-gray-200 rounded"></div>
          </div>
        ))}
      </div>
    );
  }

  if (invoices.length === 0) {
    return (
      <div className="text-center py-12">
        <DocumentTextIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No invoices found</h3>
        <p className="text-gray-600 mb-4">
          {loading ? 'Loading your invoices...' : 'You haven\'t generated any invoices yet.'}
        </p>
        <Button variant="outline" asChild>
          <Link href="/billing/subscription">
            Go to Subscription
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Invoice</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Amount</TableHead>
              <TableHead>Issued Date</TableHead>
              <TableHead>Due Date</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="visible"
            >
              {paginatedInvoices.map((invoice) => (
                <motion.tr
                  key={invoice.id}
                  variants={itemVariants}
                  className="border-t transition-colors hover:bg-gray-50"
                >
                  <TableCell>
                    <div>
                      <div className="font-medium">{invoice.invoiceNumber}</div>
                      {invoice.description && (
                        <div className="text-sm text-gray-600">{invoice.description}</div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(invoice.status)}
                      <Badge variant="secondary" className={getStatusColor(invoice.status)}>
                        {invoice.status.replace('_', ' ')}
                      </Badge>
                    </div>
                    {invoice.status === 'overdue' && (
                      <div className="text-xs text-red-600 mt-1">
                        {getDaysOverdue(invoice.dueAt)} days overdue
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="font-medium">
                      {formatCurrency(invoice.totalAmount)}
                    </div>
                    {invoice.amountPaid < invoice.totalAmount && (
                      <div className="text-sm text-gray-600">
                        {formatCurrency(invoice.amountPaid)} paid
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <div>{formatDate(invoice.issuedAt)}</div>
                  </TableCell>
                  <TableCell>
                    <div className={invoice.isOverdue ? 'text-red-600 font-medium' : ''}>
                      {formatDate(invoice.dueAt)}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <EllipsisVerticalIcon className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem asChild>
                          <Link href={`/billing/invoices/${invoice.id}`}>
                            <EyeIcon className="w-4 h-4 mr-2" />
                            View Details
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => handleDownloadInvoice(invoice.id)}
                          disabled={downloadingInvoiceId === invoice.id}
                        >
                          <ArrowDownTrayIcon className="w-4 h-4 mr-2" />
                          {downloadingInvoiceId === invoice.id ? 'Downloading...' : 'Download PDF'}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </motion.tr>
              ))}
            </motion.div>
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center">
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  className={currentPage === 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                />
              </PaginationItem>

              {/* Show page numbers */}
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (currentPage <= 3) {
                  pageNum = i + 1;
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = currentPage - 2 + i;
                }

                return (
                  <PaginationItem key={pageNum}>
                    <PaginationLink
                      onClick={() => setCurrentPage(pageNum)}
                      isActive={currentPage === pageNum}
                      className="cursor-pointer"
                    >
                      {pageNum}
                    </PaginationLink>
                  </PaginationItem>
                );
              })}

              {/* Show ellipsis */}
              {totalPages > 5 && currentPage < totalPages - 2 && (
                <PaginationItem>
                  <PaginationEllipsis />
                </PaginationItem>
              )}

              <PaginationItem>
                <PaginationNext
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  className={currentPage === totalPages ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      )}

      {/* Summary */}
      <div className="mt-4 text-sm text-gray-600 text-center">
        Showing {paginatedInvoices.length} of {invoices.length} invoices
      </div>
    </div>
  );
};

export default InvoiceList;