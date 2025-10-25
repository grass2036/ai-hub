'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

type Theme = 'light' | 'dark' | 'system';
type ColorScheme = 'blue' | 'green' | 'purple' | 'orange' | 'red';

interface ThemePreferences {
  theme: Theme;
  colorScheme: ColorScheme;
  sidebarCollapsed: boolean;
  compactMode: boolean;
  animationsEnabled: boolean;
  fontSize: 'small' | 'medium' | 'large';
}

interface ThemeContextType {
  preferences: ThemePreferences;
  updateTheme: (theme: Theme) => void;
  updateColorScheme: (colorScheme: ColorScheme) => void;
  toggleSidebar: () => void;
  toggleCompactMode: () => void;
  toggleAnimations: () => void;
  updateFontSize: (fontSize: 'small' | 'medium' | 'large') => void;
  resetPreferences: () => void;
  isDarkMode: boolean;
}

const defaultPreferences: ThemePreferences = {
  theme: 'system',
  colorScheme: 'blue',
  sidebarCollapsed: false,
  compactMode: false,
  animationsEnabled: true,
  fontSize: 'medium'
};

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState<ThemePreferences>(defaultPreferences);
  const [isDarkMode, setIsDarkMode] = useState(false);

  // 从本地存储加载偏好设置
  useEffect(() => {
    const saved = localStorage.getItem('theme-preferences');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setPreferences({ ...defaultPreferences, ...parsed });
      } catch (error) {
        console.error('Failed to parse theme preferences:', error);
      }
    }
  }, []);

  // 保存偏好设置到本地存储
  useEffect(() => {
    localStorage.setItem('theme-preferences', JSON.stringify(preferences));
  }, [preferences]);

  // 应用主题
  useEffect(() => {
    const root = document.documentElement;

    let darkMode = false;
    if (preferences.theme === 'dark') {
      darkMode = true;
    } else if (preferences.theme === 'system') {
      darkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    setIsDarkMode(darkMode);

    if (darkMode) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    // 应用颜色方案
    root.className = root.className.replace(/theme-\w+/g, '');
    root.classList.add(`theme-${preferences.colorScheme}`);

    // 应用字体大小
    root.className = root.className.replace(/font-size-\w+/g, '');
    root.classList.add(`font-size-${preferences.fontSize}`);

    // 应用紧凑模式
    if (preferences.compactMode) {
      root.classList.add('compact-mode');
    } else {
      root.classList.remove('compact-mode');
    }

    // 应用动画设置
    if (preferences.animationsEnabled) {
      root.classList.remove('no-animations');
    } else {
      root.classList.add('no-animations');
    }
  }, [preferences]);

  // 监听系统主题变化
  useEffect(() => {
    if (preferences.theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = () => {
        setIsDarkMode(mediaQuery.matches);
      };

      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [preferences.theme]);

  const updateTheme = (theme: Theme) => {
    setPreferences(prev => ({ ...prev, theme }));
  };

  const updateColorScheme = (colorScheme: ColorScheme) => {
    setPreferences(prev => ({ ...prev, colorScheme }));
  };

  const toggleSidebar = () => {
    setPreferences(prev => ({ ...prev, sidebarCollapsed: !prev.sidebarCollapsed }));
  };

  const toggleCompactMode = () => {
    setPreferences(prev => ({ ...prev, compactMode: !prev.compactMode }));
  };

  const toggleAnimations = () => {
    setPreferences(prev => ({ ...prev, animationsEnabled: !prev.animationsEnabled }));
  };

  const updateFontSize = (fontSize: 'small' | 'medium' | 'large') => {
    setPreferences(prev => ({ ...prev, fontSize }));
  };

  const resetPreferences = () => {
    setPreferences(defaultPreferences);
  };

  const value: ThemeContextType = {
    preferences,
    updateTheme,
    updateColorScheme,
    toggleSidebar,
    toggleCompactMode,
    toggleAnimations,
    updateFontSize,
    resetPreferences,
    isDarkMode
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}