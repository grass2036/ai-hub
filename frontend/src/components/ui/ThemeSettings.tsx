'use client';

import { useState } from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import { FadeIn, SlideIn } from '@/components/ui/Animations';

export default function ThemeSettings() {
  const {
    preferences,
    updateTheme,
    updateColorScheme,
    toggleCompactMode,
    toggleAnimations,
    updateFontSize,
    resetPreferences,
    isDarkMode
  } = useTheme();

  const [isOpen, setIsOpen] = useState(false);

  const themes = [
    { value: 'light', label: '浅色模式', icon: '☀️' },
    { value: 'dark', label: '深色模式', icon: '🌙' },
    { value: 'system', label: '跟随系统', icon: '💻' }
  ];

  const colorSchemes = [
    { value: 'blue', label: '蓝色', color: 'bg-blue-500' },
    { value: 'green', label: '绿色', color: 'bg-green-500' },
    { value: 'purple', label: '紫色', color: 'bg-purple-500' },
    { value: 'orange', label: '橙色', color: 'bg-orange-500' },
    { value: 'red', label: '红色', color: 'bg-red-500' }
  ];

  const fontSizes = [
    { value: 'small', label: '小', preview: 'text-sm' },
    { value: 'medium', label: '中', preview: 'text-base' },
    { value: 'large', label: '大', preview: 'text-lg' }
  ];

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 p-3 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-colors"
        title="主题设置"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
        </svg>
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="fixed inset-0 bg-black bg-opacity-25" onClick={() => setIsOpen(false)} />

        <SlideIn direction="up" className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
          <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">个性化设置</h2>
              <button
                onClick={() => setIsOpen(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          <div className="p-6 space-y-6">
            {/* 主题选择 */}
            <FadeIn delay={100}>
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">主题模式</h3>
                <div className="grid grid-cols-1 gap-3">
                  {themes.map((theme) => (
                    <button
                      key={theme.value}
                      onClick={() => updateTheme(theme.value as any)}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        preferences.theme === theme.value
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <span className="text-2xl">{theme.icon}</span>
                        <span className="font-medium text-gray-900 dark:text-white">{theme.label}</span>
                        {preferences.theme === theme.value && (
                          <div className="ml-auto">
                            <div className="w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center">
                              <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                              </svg>
                            </div>
                          </div>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </FadeIn>

            {/* 颜色方案 */}
            <FadeIn delay={200}>
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">主题颜色</h3>
                <div className="grid grid-cols-5 gap-3">
                  {colorSchemes.map((scheme) => (
                    <button
                      key={scheme.value}
                      onClick={() => updateColorScheme(scheme.value as any)}
                      className={`relative p-4 rounded-lg border-2 transition-all ${
                        preferences.colorScheme === scheme.value
                          ? 'border-gray-900 dark:border-white'
                          : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'
                      }`}
                    >
                      <div className={`w-8 h-8 ${scheme.color} rounded-full mx-auto mb-2`} />
                      <span className="text-xs font-medium text-gray-900 dark:text-white">{scheme.label}</span>
                      {preferences.colorScheme === scheme.value && (
                        <div className="absolute -top-1 -right-1 w-3 h-3 bg-gray-900 dark:bg-white rounded-full" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            </FadeIn>

            {/* 字体大小 */}
            <FadeIn delay={300}>
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">字体大小</h3>
                <div className="grid grid-cols-3 gap-3">
                  {fontSizes.map((size) => (
                    <button
                      key={size.value}
                      onClick={() => updateFontSize(size.value as any)}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        preferences.fontSize === size.value
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'
                      }`}
                    >
                      <span className={`font-medium text-gray-900 dark:text-white ${size.preview}`}>
                        {size.label}
                      </span>
                      {preferences.fontSize === size.value && (
                        <div className="mt-2">
                          <div className="w-4 h-4 bg-blue-500 rounded-full mx-auto" />
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            </FadeIn>

            {/* 其他设置 */}
            <FadeIn delay={400}>
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">其他设置</h3>
                <div className="space-y-3">
                  <label className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg cursor-pointer">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">紧凑模式</div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">减少界面元素间距</div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        toggleCompactMode();
                      }}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        preferences.compactMode ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          preferences.compactMode ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </label>

                  <label className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg cursor-pointer">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">动画效果</div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">启用界面过渡动画</div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        toggleAnimations();
                      }}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        preferences.animationsEnabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          preferences.animationsEnabled ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </label>
                </div>
              </div>
            </FadeIn>

            {/* 重置按钮 */}
            <FadeIn delay={500}>
              <div className="pt-4 border-t border-gray-200 dark:border-gray-600">
                <button
                  onClick={resetPreferences}
                  className="w-full py-3 px-4 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                >
                  恢复默认设置
                </button>
              </div>
            </FadeIn>
          </div>
        </SlideIn>
      </div>
    </div>
  );
}