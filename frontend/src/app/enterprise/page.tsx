/**
 * 企业管理页面
 * 提供企业级多租户管理界面
 */

"use client";

import TenantDashboard from '@/components/enterprise/TenantDashboard';

export default function EnterprisePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <TenantDashboard />
    </div>
  );
}