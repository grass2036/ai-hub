'use client';

import React from 'react';
import { useI18n } from '@/contexts/I18nContext';

export default function CulturalAdaptationTest() {
  const { t, language, formatDate, formatTime, formatNumber, formatCurrency, availableLanguages } = useI18n();

  const testDate = new Date('2024-12-25T15:30:00');
  const testNumber = 1234567.89;
  const testCurrency = 1000.50;

  return (
    <div className="p-6 bg-white rounded-lg shadow-md max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">文化适配测试 (Cultural Adaptation Test)</h2>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">选择语言 / Select Language:</label>
        <select
          value={language}
          onChange={(e) => {
            // 这里应该调用setLanguage函数，但为了演示暂时只显示
            console.log('Language changed to:', e.target.value);
          }}
          className="w-full p-2 border rounded-md"
        >
          {Object.entries(availableLanguages).map(([code, config]) => (
            <option key={code} value={code}>
              {config.flag} {config.nativeName} ({config.name})
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 语言信息 */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">语言配置 / Language Config</h3>
          <div className="bg-gray-50 p-4 rounded">
            <p><strong>当前语言:</strong> {language}</p>
            <p><strong>语言名称:</strong> {availableLanguages[language]?.name}</p>
            <p><strong>本地名称:</strong> {availableLanguages[language]?.nativeName}</p>
            <p><strong>RTL:</strong> {availableLanguages[language]?.rtl ? '是' : '否'}</p>
            <p><strong>日期格式:</strong> {availableLanguages[language]?.dateFormat}</p>
            <p><strong>时间格式:</strong> {availableLanguages[language]?.timeFormat}</p>
            <p><strong>货币:</strong> {availableLanguages[language]?.currency}</p>
          </div>
        </div>

        {/* 日期时间格式测试 */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">日期时间格式 / Date & Time</h3>
          <div className="bg-gray-50 p-4 rounded">
            <p><strong>测试日期:</strong> {testDate.toLocaleString()}</p>
            <p><strong>格式化日期:</strong> {formatDate(testDate)}</p>
            <p><strong>格式化时间:</strong> {formatTime(testDate)}</p>
            <p><strong>相对时间:</strong> {formatRelativeTime(testDate, language as any)}</p>
          </div>
        </div>

        {/* 数字格式测试 */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">数字格式 / Number Format</h3>
          <div className="bg-gray-50 p-4 rounded">
            <p><strong>原始数字:</strong> {testNumber}</p>
            <p><strong>格式化数字:</strong> {formatNumber(testNumber)}</p>
            <p><strong>百分比:</strong> {formatPercentage(testNumber / 10000, language as any)}</p>
            <p><strong>文件大小:</strong> {formatFileSize(1048576, language as any)}</p>
          </div>
        </div>

        {/* 货币格式测试 */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">货币格式 / Currency Format</h3>
          <div className="bg-gray-50 p-4 rounded">
            <p><strong>原始金额:</strong> ${testCurrency}</p>
            <p><strong>本地货币:</strong> {formatCurrency(testCurrency)}</p>
            <p><strong>美元:</strong> {formatCurrency(testCurrency, 'USD')}</p>
            <p><strong>欧元:</strong> {formatCurrency(testCurrency, 'EUR')}</p>
            <p><strong>人民币:</strong> {formatCurrency(testCurrency, 'CNY')}</p>
          </div>
        </div>
      </div>

      {/* 文本翻译测试 */}
      <div className="mt-6">
        <h3 className="text-lg font-semibold mb-4">文本翻译测试 / Text Translation Test</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 p-4 rounded">
            <h4 className="font-medium">常用文本 / Common</h4>
            <p>{t('common.loading')}</p>
            <p>{t('common.save')}</p>
            <p>{t('common.cancel')}</p>
          </div>
          <div className="bg-green-50 p-4 rounded">
            <h4 className="font-medium">导航 / Navigation</h4>
            <p>{t('navigation.dashboard')}</p>
            <p>{t('navigation.chat')}</p>
            <p>{t('navigation.settings')}</p>
          </div>
          <div className="bg-purple-50 p-4 rounded">
            <h4 className="font-medium">成功消息 / Success</h4>
            <p>{t('success.operation_completed')}</p>
            <p>{t('success.data_saved')}</p>
          </div>
        </div>
      </div>

      {/* 参数化翻译测试 */}
      <div className="mt-6">
        <h3 className="text-lg font-semibold mb-4">参数化翻译 / Parameterized Translation</h3>
        <div className="bg-yellow-50 p-4 rounded">
          <p><strong>带参数的翻译示例:</strong></p>
          <p>{t('auth.welcome_back', { name: 'John' })}</p>
          <p>{t('dashboard.requests_today', { count: 42 })}</p>
          <p>{t('billing.monthly_cost', { amount: formatCurrency(99.99) })}</p>
        </div>
      </div>
    </div>
  );
}

// 辅助函数
function formatRelativeTime(date: Date, language: string): string {
  const rtf = new Intl.RelativeTimeFormat(language, { numeric: 'auto' });
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  return rtf.format(-diffDays, 'day');
}

function formatPercentage(value: number, language: string): string {
  return new Intl.NumberFormat(language, {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);
}

function formatFileSize(bytes: number, language: string): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`;
}