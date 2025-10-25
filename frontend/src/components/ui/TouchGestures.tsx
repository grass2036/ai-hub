'use client';

import { useEffect, useRef, useState } from 'react';

interface TouchGestureProps {
  children: React.ReactNode;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
  onTap?: () => void;
  onLongPress?: () => void;
  className?: string;
}

export default function TouchGestures({
  children,
  onSwipeLeft,
  onSwipeRight,
  onSwipeUp,
  onSwipeDown,
  onTap,
  onLongPress,
  className = ''
}: TouchGestureProps) {
  const touchStartRef = useRef({ x: 0, y: 0, time: 0 });
  const [isLongPress, setIsLongPress] = useState(false);
  const longPressTimerRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    const handleTouchStart = (e: TouchEvent) => {
      const touch = e.touches[0];
      touchStartRef.current = {
        x: touch.clientX,
        y: touch.clientY,
        time: Date.now()
      };

      // 设置长按检测
      if (onLongPress) {
        setIsLongPress(false);
        longPressTimerRef.current = setTimeout(() => {
          setIsLongPress(true);
          onLongPress();
        }, 500); // 500ms 长按
      }
    };

    const handleTouchEnd = (e: TouchEvent) => {
      // 清除长按定时器
      if (longPressTimerRef.current) {
        clearTimeout(longPressTimerRef.current);
      }

      if (isLongPress) return; // 如果是长按，不处理其他手势

      const touch = e.changedTouches[0];
      const deltaX = touch.clientX - touchStartRef.current.x;
      const deltaY = touch.clientY - touchStartRef.current.y;
      const deltaTime = Date.now() - touchStartRef.current.time;

      // 最小滑动距离和时间阈值
      const minDistance = 50;
      const maxTime = 300;

      if (Math.abs(deltaX) < 10 && Math.abs(deltaY) < 10 && deltaTime < 200) {
        // 点击
        onTap?.();
      } else if (deltaTime < maxTime) {
        // 滑动手势
        if (Math.abs(deltaX) > Math.abs(deltaY)) {
          // 水平滑动
          if (deltaX > minDistance) {
            onSwipeRight?.();
          } else if (deltaX < -minDistance) {
            onSwipeLeft?.();
          }
        } else {
          // 垂直滑动
          if (deltaY > minDistance) {
            onSwipeDown?.();
          } else if (deltaY < -minDistance) {
            onSwipeUp?.();
          }
        }
      }
    };

    const element = document.querySelector(`[touch-gesture-wrapper="${className}"]`);
    if (element) {
      element.addEventListener('touchstart', handleTouchStart, { passive: true });
      element.addEventListener('touchend', handleTouchEnd, { passive: true });

      return () => {
        element.removeEventListener('touchstart', handleTouchStart);
        element.removeEventListener('touchend', handleTouchEnd);
        if (longPressTimerRef.current) {
          clearTimeout(longPressTimerRef.current);
        }
      };
    }
  }, [onSwipeLeft, onSwipeRight, onSwipeUp, onSwipeDown, onTap, onLongPress, isLongPress, className]);

  return (
    <div touch-gesture-wrapper={className} className={className}>
      {children}
    </div>
  );
}

// Hook for swipe gestures on specific elements
export function useSwipeGestures() {
  const addSwipeGestures = (
    element: HTMLElement,
    gestures: {
      onSwipeLeft?: () => void;
      onSwipeRight?: () => void;
      onSwipeUp?: () => void;
      onSwipeDown?: () => void;
    }
  ) => {
    let touchStart: { x: number; y: number; time: number } | null = null;

    const handleTouchStart = (e: TouchEvent) => {
      const touch = e.touches[0];
      touchStart = {
        x: touch.clientX,
        y: touch.clientY,
        time: Date.now()
      };
    };

    const handleTouchEnd = (e: TouchEvent) => {
      if (!touchStart) return;

      const touch = e.changedTouches[0];
      const deltaX = touch.clientX - touchStart.x;
      const deltaY = touch.clientY - touchStart.y;
      const deltaTime = Date.now() - touchStart.time;

      const minDistance = 50;
      const maxTime = 300;

      if (deltaTime < maxTime) {
        if (Math.abs(deltaX) > Math.abs(deltaY)) {
          if (deltaX > minDistance) {
            gestures.onSwipeRight?.();
          } else if (deltaX < -minDistance) {
            gestures.onSwipeLeft?.();
          }
        } else {
          if (deltaY > minDistance) {
            gestures.onSwipeDown?.();
          } else if (deltaY < -minDistance) {
            gestures.onSwipeUp?.();
          }
        }
      }

      touchStart = null;
    };

    element.addEventListener('touchstart', handleTouchStart, { passive: true });
    element.addEventListener('touchend', handleTouchEnd, { passive: true });

    return () => {
      element.removeEventListener('touchstart', handleTouchStart);
      element.removeEventListener('touchend', handleTouchEnd);
    };
  };

  return { addSwipeGestures };
}