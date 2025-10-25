/**
 * 性能优化工具函数
 */

// 缓存管理
class CacheManager {
  private cache = new Map<string, { data: any; timestamp: number; ttl: number }>();

  set(key: string, data: any, ttl: number = 300000): void { // 默认5分钟
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl
    });
  }

  get(key: string): any | null {
    const item = this.cache.get(key);
    if (!item) return null;

    if (Date.now() - item.timestamp > item.ttl) {
      this.cache.delete(key);
      return null;
    }

    return item.data;
  }

  clear(): void {
    this.cache.clear();
  }

  delete(key: string): void {
    this.cache.delete(key);
  }

  size(): number {
    return this.cache.size;
  }
}

export const cacheManager = new CacheManager();

// 防抖函数
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

// 节流函数
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

// 内存监控
export function useMemoryMonitor() {
  const [memoryInfo, setMemoryInfo] = useState<any>(null);

  useEffect(() => {
    if ('memory' in performance) {
      const updateMemoryInfo = () => {
        setMemoryInfo((performance as any).memory);
      };

      updateMemoryInfo();
      const interval = setInterval(updateMemoryInfo, 5000);

      return () => clearInterval(interval);
    }
  }, []);

  return memoryInfo;
}

// 性能监控
export class PerformanceMonitor {
  private static instance: PerformanceMonitor;
  private metrics: Map<string, number[]> = new Map();

  static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor();
    }
    return PerformanceMonitor.instance;
  }

  startMeasure(name: string): void {
    performance.mark(`${name}-start`);
  }

  endMeasure(name: string): number {
    performance.mark(`${name}-end`);
    performance.measure(name, `${name}-start`, `${name}-end`);

    const measure = performance.getEntriesByName(name, 'measure')[0];
    if (measure) {
      this.recordMetric(name, measure.duration);
      return measure.duration;
    }
    return 0;
  }

  recordMetric(name: string, value: number): void {
    if (!this.metrics.has(name)) {
      this.metrics.set(name, []);
    }
    this.metrics.get(name)!.push(value);
  }

  getMetricStats(name: string): { avg: number; min: number; max: number; count: number } | null {
    const values = this.metrics.get(name);
    if (!values || values.length === 0) return null;

    const avg = values.reduce((sum, val) => sum + val, 0) / values.length;
    const min = Math.min(...values);
    const max = Math.max(...values);

    return { avg, min, max, count: values.length };
  }

  getAllMetrics(): Record<string, { avg: number; min: number; max: number; count: number }> {
    const result: Record<string, { avg: number; min: number; max: number; count: number }> = {};

    for (const [name] of this.metrics) {
      const stats = this.getMetricStats(name);
      if (stats) {
        result[name] = stats;
      }
    }

    return result;
  }
}

export const performanceMonitor = PerformanceMonitor.getInstance();

// 资源预加载
export function preloadImage(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve();
    img.onerror = reject;
    img.src = src;
  });
}

export function preloadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.onload = () => resolve();
    script.onerror = reject;
    script.src = src;
    document.head.appendChild(script);
  });
}

// 批量请求处理
export class BatchRequestManager {
  private static instance: BatchRequestManager;
  private pendingRequests: Map<string, {
    resolve: (value: any) => void;
    reject: (error: any) => void;
  }[]> = new Map();
  private batchTimeout: NodeJS.Timeout | null = null;

  static getInstance(): BatchRequestManager {
    if (!BatchRequestManager.instance) {
      BatchRequestManager.instance = new BatchRequestManager();
    }
    return BatchRequestManager.instance;
  }

  async request<T>(key: string, requestFn: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      if (!this.pendingRequests.has(key)) {
        this.pendingRequests.set(key, []);
      }

      this.pendingRequests.get(key)!.push({ resolve, reject });

      if (!this.batchTimeout) {
        this.batchTimeout = setTimeout(() => {
          this.processBatch(key, requestFn);
        }, 50); // 50ms 延迟批量处理
      }
    });
  }

  private async processBatch<T>(key: string, requestFn: () => Promise<T>): Promise<void> {
    const requests = this.pendingRequests.get(key) || [];
    this.pendingRequests.delete(key);
    this.batchTimeout = null;

    try {
      const result = await requestFn();
      requests.forEach(({ resolve }) => resolve(result));
    } catch (error) {
      requests.forEach(({ reject }) => reject(error));
    }
  }
}

export const batchRequestManager = BatchRequestManager.getInstance();

// Web Workers 管理
export class WorkerManager {
  private workers: Map<string, Worker> = new Map();
  private taskQueue: Map<string, {
    task: any;
    resolve: (result: any) => void;
    reject: (error: any) => void;
  }[]> = new Map();

  async createWorker(name: string, scriptPath: string): Promise<void> {
    if (this.workers.has(name)) return;

    try {
      const worker = new Worker(scriptPath);
      worker.onmessage = (e) => {
        const { id, result, error } = e.data;
        const queue = this.taskQueue.get(name);
        if (queue && queue.length > 0) {
          const { resolve, reject } = queue.shift()!;
          if (error) {
            reject(new Error(error));
          } else {
            resolve(result);
          }
        }
      };

      this.workers.set(name, worker);
      this.taskQueue.set(name, []);
    } catch (error) {
      console.error(`Failed to create worker ${name}:`, error);
    }
  }

  async runTask<T>(workerName: string, task: any): Promise<T> {
    const worker = this.workers.get(workerName);
    const queue = this.taskQueue.get(workerName);

    if (!worker || !queue) {
      throw new Error(`Worker ${workerName} not found`);
    }

    return new Promise((resolve, reject) => {
      queue.push({ task, resolve, reject });
      worker.postMessage({ id: Date.now(), task });
    });
  }

  terminateWorker(name: string): void {
    const worker = this.workers.get(name);
    if (worker) {
      worker.terminate();
      this.workers.delete(name);
      this.taskQueue.delete(name);
    }
  }

  terminateAll(): void {
    for (const [name] of this.workers) {
      this.terminateWorker(name);
    }
  }
}

export const workerManager = new WorkerManager();

// 代码分割辅助函数
export async function loadComponent<T>(
  importFn: () => Promise<{ default: T }>
): Promise<T> {
  try {
    const module = await importFn();
    return module.default;
  } catch (error) {
    console.error('Failed to load component:', error);
    throw error;
  }
}

// 智能图片优化
export function getOptimizedImageUrl(
  src: string,
  width?: number,
  height?: number,
  quality: number = 80
): string {
  // 如果是外部URL，直接返回
  if (src.startsWith('http')) {
    return src;
  }

  // 这里可以集成CDN或图片处理服务
  let optimizedSrc = src;

  if (width || height) {
    const params = new URLSearchParams();
    if (width) params.append('w', width.toString());
    if (height) params.append('h', height.toString());
    params.append('q', quality.toString());

    optimizedSrc += `?${params.toString()}`;
  }

  return optimizedSrc;
}

// 网络状态检测
export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [connectionType, setConnectionType] = useState<string>('unknown');

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // 检测网络连接类型
    if ('connection' in navigator) {
      const connection = (navigator as any).connection;
      setConnectionType(connection.effectiveType || 'unknown');

      const handleConnectionChange = () => {
        setConnectionType(connection.effectiveType || 'unknown');
      };

      connection.addEventListener('change', handleConnectionChange);

      return () => {
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
        connection.removeEventListener('change', handleConnectionChange);
      };
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return { isOnline, connectionType };
}