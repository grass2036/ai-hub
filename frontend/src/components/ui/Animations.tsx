'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';

// 页面过渡动画组件
interface PageTransitionProps {
  children: React.ReactNode;
  className?: string;
}

export function PageTransition({ children, className = '' }: PageTransitionProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  return (
    <div
      className={`
        transition-all duration-300 ease-in-out transform
        ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}
        ${className}
      `}
    >
      {children}
    </div>
  );
}

// 淡入动画组件
interface FadeInProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  className?: string;
}

export function FadeIn({ children, delay = 0, duration = 500, className = '' }: FadeInProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, delay);

    return () => clearTimeout(timer);
  }, [delay]);

  return (
    <div
      className={`
        transition-opacity ease-in-out
        ${isVisible ? 'opacity-100' : 'opacity-0'}
        ${className}
      `}
      style={{ transitionDuration: `${duration}ms` }}
    >
      {children}
    </div>
  );
}

// 滑入动画组件
interface SlideInProps {
  children: React.ReactNode;
  direction?: 'up' | 'down' | 'left' | 'right';
  delay?: number;
  distance?: number;
  className?: string;
}

export function SlideIn({
  children,
  direction = 'up',
  delay = 0,
  distance = 20,
  className = ''
}: SlideInProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, delay);

    return () => clearTimeout(timer);
  }, [delay]);

  const getTransform = () => {
    switch (direction) {
      case 'up':
        return `translateY(${isVisible ? 0 : distance}px)`;
      case 'down':
        return `translateY(${isVisible ? 0 : -distance}px)`;
      case 'left':
        return `translateX(${isVisible ? 0 : distance}px)`;
      case 'right':
        return `translateX(${isVisible ? 0 : -distance}px)`;
      default:
        return `translateY(${isVisible ? 0 : distance}px)`;
    }
  };

  return (
    <div
      className={`
        transition-all ease-out
        ${isVisible ? 'opacity-100' : 'opacity-0'}
        ${className}
      `}
      style={{
        transform: getTransform(),
        transitionDuration: '300ms',
        transitionDelay: `${delay}ms`
      }}
    >
      {children}
    </div>
  );
}

// 缩放动画组件
interface ScaleInProps {
  children: React.ReactNode;
  delay?: number;
  from?: number;
  to?: number;
  className?: string;
}

export function ScaleIn({
  children,
  delay = 0,
  from = 0.8,
  to = 1,
  className = ''
}: ScaleInProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, delay);

    return () => clearTimeout(timer);
  }, [delay]);

  return (
    <div
      className={`
        transition-transform ease-out
        ${isVisible ? 'opacity-100' : 'opacity-0'}
        ${className}
      `}
      style={{
        transform: `scale(${isVisible ? to : from})`,
        transitionDuration: '300ms',
        transitionDelay: `${delay}ms`
      }}
    >
      {children}
    </div>
  );
}

// 弹跳动画组件
interface BounceProps {
  children: React.ReactNode;
  trigger?: boolean;
  className?: string;
}

export function Bounce({ children, trigger = true, className = '' }: BounceProps) {
  const [isBouncing, setIsBouncing] = useState(false);

  useEffect(() => {
    if (trigger) {
      setIsBouncing(true);
      const timer = setTimeout(() => setIsBouncing(false), 600);
      return () => clearTimeout(timer);
    }
  }, [trigger]);

  return (
    <div
      className={`
        ${isBouncing ? 'animate-bounce' : ''}
        ${className}
      `}
    >
      {children}
    </div>
  );
}

// 脉冲动画组件
interface PulseProps {
  children: React.ReactNode;
  intensity?: 'light' | 'medium' | 'strong';
  className?: string;
}

export function Pulse({ children, intensity = 'medium', className = '' }: PulseProps) {
  const intensityClasses = {
    light: 'animate-pulse',
    medium: 'animate-pulse',
    strong: 'animate-ping'
  };

  return (
    <div className={`${intensityClasses[intensity]} ${className}`}>
      {children}
    </div>
  );
}

// 加载状态骨架屏
interface SkeletonProps {
  lines?: number;
  className?: string;
}

export function Skeleton({ lines = 3, className = '' }: SkeletonProps) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`
            h-4 bg-gray-200 rounded animate-pulse
            ${i === lines - 1 ? 'w-3/4' : 'w-full'}
          `}
        />
      ))}
    </div>
  );
}

// 列表项交错动画
interface StaggeredListProps {
  children: React.ReactNode[];
  staggerDelay?: number;
  className?: string;
}

export function StaggeredList({
  children,
  staggerDelay = 100,
  className = ''
}: StaggeredListProps) {
  return (
    <div className={className}>
      {children.map((child, index) => (
        <FadeIn key={index} delay={index * staggerDelay}>
          {child}
        </FadeIn>
      ))}
    </div>
  );
}

// 通知弹窗动画
interface NotificationProps {
  children: React.ReactNode;
  isVisible: boolean;
  onClose: () => void;
  type?: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
}

export function Notification({
  children,
  isVisible,
  onClose,
  type = 'info',
  duration = 3000
}: NotificationProps) {
  const [shouldRender, setShouldRender] = useState(isVisible);

  useEffect(() => {
    if (isVisible) {
      setShouldRender(true);
      if (duration > 0) {
        const timer = setTimeout(() => {
          onClose();
        }, duration);
        return () => clearTimeout(timer);
      }
    } else {
      const timer = setTimeout(() => setShouldRender(false), 300);
      return () => clearTimeout(timer);
    }
  }, [isVisible, duration, onClose]);

  if (!shouldRender) return null;

  const typeStyles = {
    success: 'bg-green-500 text-white',
    error: 'bg-red-500 text-white',
    warning: 'bg-yellow-500 text-black',
    info: 'bg-blue-500 text-white'
  };

  return (
    <div
      className={`
        fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg
        transition-all duration-300 ease-in-out transform
        ${isVisible
          ? 'translate-x-0 opacity-100'
          : 'translate-x-full opacity-0'
        }
        ${typeStyles[type]}
      `}
    >
      <div className="flex items-center justify-between">
        <div>{children}</div>
        <button
          onClick={onClose}
          className="ml-4 text-white hover:text-gray-200"
        >
          ×
        </button>
      </div>
    </div>
  );
}

// 进度条动画
interface ProgressBarProps {
  progress: number;
  className?: string;
  showPercentage?: boolean;
  color?: 'blue' | 'green' | 'red' | 'yellow';
}

export function ProgressBar({
  progress,
  className = '',
  showPercentage = false,
  color = 'blue'
}: ProgressBarProps) {
  const [displayProgress, setDisplayProgress] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDisplayProgress(progress);
    }, 100);
    return () => clearTimeout(timer);
  }, [progress]);

  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    red: 'bg-red-500',
    yellow: 'bg-yellow-500'
  };

  return (
    <div className={`w-full ${className}`}>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`
            ${colorClasses[color]} h-2 rounded-full transition-all duration-500 ease-out
          `}
          style={{ width: `${Math.min(100, Math.max(0, displayProgress))}%` }}
        />
      </div>
      {showPercentage && (
        <div className="text-center mt-1 text-sm text-gray-600">
          {Math.round(displayProgress)}%
        </div>
      )}
    </div>
  );
}