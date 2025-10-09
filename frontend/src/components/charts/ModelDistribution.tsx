'use client';

import { useEffect, useRef, useState } from 'react';

interface ModelData {
  model: string;
  requests: number;
  percentage: number;
  color: string;
}

interface ModelDistributionProps {
  data: ModelData[];
  title?: string;
  size?: number;
}

const COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#84cc16', // lime
];

export default function ModelDistribution({ data, title = '模型使用分布', size = 300 }: ModelDistributionProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredSegment, setHoveredSegment] = useState<number | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 设置画布大小
    const scale = window.devicePixelRatio;
    canvas.width = size * scale;
    canvas.height = size * scale;
    ctx.scale(scale, scale);

    // 清空画布
    ctx.clearRect(0, 0, size, size);

    if (data.length === 0) return;

    const centerX = size / 2;
    const centerY = size / 2;
    const radius = size / 2 - 20;

    // 计算角度
    let currentAngle = -Math.PI / 2; // 从顶部开始

    data.forEach((segment, index) => {
      const sliceAngle = (segment.percentage / 100) * 2 * Math.PI;

      // 如果是悬停的段落，稍微偏移
      const isHovered = hoveredSegment === index;
      const offset = isHovered ? 10 : 0;
      const middleAngle = currentAngle + sliceAngle / 2;
      const offsetX = Math.cos(middleAngle) * offset;
      const offsetY = Math.sin(middleAngle) * offset;

      // 绘制饼图段
      ctx.beginPath();
      ctx.moveTo(centerX + offsetX, centerY + offsetY);
      ctx.arc(centerX + offsetX, centerY + offsetY, radius, currentAngle, currentAngle + sliceAngle);
      ctx.closePath();
      ctx.fillStyle = segment.color || COLORS[index % COLORS.length];
      ctx.fill();

      // 绘制边框
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.stroke();

      // 绘制百分比标签
      if (segment.percentage > 5) { // 只在大于5%的段落显示标签
        const labelAngle = currentAngle + sliceAngle / 2;
        const labelX = centerX + offsetX + Math.cos(labelAngle) * (radius * 0.7);
        const labelY = centerY + offsetY + Math.sin(labelAngle) * (radius * 0.7);

        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 14px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${segment.percentage.toFixed(1)}%`, labelX, labelY);
      }

      currentAngle += sliceAngle;
    });

    // 绘制中心圆（甜甜圈效果）
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.3, 0, 2 * Math.PI);
    ctx.fillStyle = '#ffffff';
    ctx.fill();

  }, [data, size, hoveredSegment]);

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const centerX = size / 2;
    const centerY = size / 2;
    const radius = size / 2 - 20;

    // 计算鼠标到中心的距离和角度
    const dx = x - centerX;
    const dy = y - centerY;
    const distance = Math.sqrt(dx * dx + dy * dy);

    // 检查是否在饼图范围内
    if (distance > radius * 0.3 && distance < radius) {
      let angle = Math.atan2(dy, dx);
      if (angle < -Math.PI / 2) angle += 2 * Math.PI;

      // 找到对应的段落
      let currentAngle = -Math.PI / 2;
      for (let i = 0; i < data.length; i++) {
        const sliceAngle = (data[i].percentage / 100) * 2 * Math.PI;
        if (angle >= currentAngle && angle < currentAngle + sliceAngle) {
          setHoveredSegment(i);
          setTooltipPosition({ x: e.clientX, y: e.clientY });
          return;
        }
        currentAngle += sliceAngle;
      }
    }

    setHoveredSegment(null);
    setTooltipPosition(null);
  };

  const handleMouseLeave = () => {
    setHoveredSegment(null);
    setTooltipPosition(null);
  };

  // 为数据分配颜色
  const coloredData = data.map((item, index) => ({
    ...item,
    color: item.color || COLORS[index % COLORS.length]
  }));

  return (
    <div className="flex flex-col items-center">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>

      <div className="relative">
        <canvas
          ref={canvasRef}
          className="border border-gray-200 rounded-lg"
          style={{ width: size, height: size }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        />

        {/* 悬停提示 */}
        {hoveredSegment !== null && tooltipPosition && data[hoveredSegment] && (
          <div
            className="absolute z-10 bg-gray-900 text-white p-3 rounded-lg shadow-lg pointer-events-none"
            style={{
              left: tooltipPosition.x + 10,
              top: tooltipPosition.y - 40,
              maxWidth: '200px'
            }}
          >
            <div className="font-medium text-sm mb-1">
              {data[hoveredSegment].model}
            </div>
            <div className="text-xs space-y-1">
              <div>请求数: {data[hoveredSegment].requests.toLocaleString()}</div>
              <div>占比: {data[hoveredSegment].percentage.toFixed(1)}%</div>
            </div>
          </div>
        )}
      </div>

      {/* 图例 */}
      <div className="mt-6 space-y-2">
        {coloredData.map((item, index) => (
          <div key={index} className="flex items-center space-x-3">
            <div
              className="w-4 h-4 rounded"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-sm text-gray-700">{item.model}</span>
            <span className="text-sm text-gray-500 ml-auto">
              {item.requests.toLocaleString()} ({item.percentage.toFixed(1)}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}