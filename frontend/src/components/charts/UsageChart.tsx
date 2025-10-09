'use client';

import { useEffect, useRef, useState } from 'react';

interface UsageData {
  date: string;
  requests: number;
  cost: number;
}

interface UsageChartProps {
  data: UsageData[];
  title: string;
  type: 'requests' | 'cost';
  height?: number;
}

export default function UsageChart({ data, title, type, height = 300 }: UsageChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredPoint, setHoveredPoint] = useState<{ x: number; y: number; value: number; date: string } | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 设置画布大小
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    // 清空画布
    ctx.clearRect(0, 0, rect.width, height);

    if (data.length === 0) return;

    const padding = { top: 20, right: 40, bottom: 40, left: 60 };
    const chartWidth = rect.width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    // 找出最大值和最小值
    const values = data.map(d => type === 'requests' ? d.requests : d.cost);
    const maxValue = Math.max(...values, 1);
    const minValue = Math.min(...values, 0);

    // 绘制网格线
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;
    ctx.setLineDash([5, 5]);

    // 横向网格线
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (chartHeight * i) / 5;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(padding.left + chartWidth, y);
      ctx.stroke();

      // Y轴标签
      const value = maxValue - ((maxValue - minValue) * i) / 5;
      ctx.fillStyle = '#6b7280';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'right';
      const label = type === 'requests'
        ? value.toLocaleString()
        : `$${value.toFixed(2)}`;
      ctx.fillText(label, padding.left - 10, y + 4);
    }

    ctx.setLineDash([]);

    // 绘制数据线
    const gradient = ctx.createLinearGradient(0, padding.top, 0, height - padding.bottom);
    gradient.addColorStop(0, type === 'requests' ? 'rgba(59, 130, 246, 0.8)' : 'rgba(16, 185, 129, 0.8)');
    gradient.addColorStop(1, type === 'requests' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(16, 185, 129, 0.1)');

    ctx.beginPath();
    data.forEach((point, index) => {
      const x = padding.left + (chartWidth * index) / (data.length - 1);
      const value = type === 'requests' ? point.requests : point.cost;
      const y = padding.top + chartHeight - ((value - minValue) / (maxValue - minValue)) * chartHeight;

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });

    // 绘制填充区域
    ctx.lineTo(padding.left + chartWidth, height - padding.bottom);
    ctx.lineTo(padding.left, height - padding.bottom);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // 绘制线条
    ctx.beginPath();
    data.forEach((point, index) => {
      const x = padding.left + (chartWidth * index) / (data.length - 1);
      const value = type === 'requests' ? point.requests : point.cost;
      const y = padding.top + chartHeight - ((value - minValue) / (maxValue - minValue)) * chartHeight;

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.strokeStyle = type === 'requests' ? '#3b82f6' : '#10b981';
    ctx.lineWidth = 2;
    ctx.stroke();

    // 绘制数据点
    data.forEach((point, index) => {
      const x = padding.left + (chartWidth * index) / (data.length - 1);
      const value = type === 'requests' ? point.requests : point.cost;
      const y = padding.top + chartHeight - ((value - minValue) / (maxValue - minValue)) * chartHeight;

      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.fill();
      ctx.strokeStyle = type === 'requests' ? '#3b82f6' : '#10b981';
      ctx.lineWidth = 2;
      ctx.stroke();
    });

    // 绘制X轴标签
    ctx.fillStyle = '#6b7280';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';

    const labelInterval = Math.ceil(data.length / 8); // 最多显示8个标签
    data.forEach((point, index) => {
      if (index % labelInterval === 0 || index === data.length - 1) {
        const x = padding.left + (chartWidth * index) / (data.length - 1);
        const date = new Date(point.date);
        const label = `${date.getMonth() + 1}/${date.getDate()}`;
        ctx.fillText(label, x, height - padding.bottom + 20);
      }
    });

  }, [data, type, height]);

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const padding = { top: 20, right: 40, bottom: 40, left: 60 };
    const chartWidth = rect.width - padding.left - padding.right;

    if (x < padding.left || x > padding.left + chartWidth) {
      setHoveredPoint(null);
      return;
    }

    const dataIndex = Math.round(((x - padding.left) / chartWidth) * (data.length - 1));
    if (dataIndex >= 0 && dataIndex < data.length) {
      const point = data[dataIndex];
      setHoveredPoint({
        x: e.clientX,
        y: e.clientY,
        value: type === 'requests' ? point.requests : point.cost,
        date: new Date(point.date).toLocaleDateString()
      });
    }
  };

  return (
    <div className="relative">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <canvas
        ref={canvasRef}
        className="w-full border border-gray-200 rounded-lg"
        style={{ height: `${height}px` }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredPoint(null)}
      />

      {hoveredPoint && (
        <div
          className="absolute z-10 bg-gray-900 text-white p-2 rounded-lg text-sm pointer-events-none"
          style={{
            left: hoveredPoint.x + 10,
            top: hoveredPoint.y - 40,
          }}
        >
          <div className="font-medium">{hoveredPoint.date}</div>
          <div>
            {type === 'requests'
              ? `${hoveredPoint.value.toLocaleString()} 请求`
              : `$${hoveredPoint.value.toFixed(2)}`
            }
          </div>
        </div>
      )}
    </div>
  );
}