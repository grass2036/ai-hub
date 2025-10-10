'use client';

import { useEffect, useRef } from 'react';

interface UsageData {
  date: string;
  requests: number;
  cost: number;
  tokens: number;
}

interface UsageTrendChartProps {
  data: UsageData[];
  title?: string;
  height?: number;
  showCost?: boolean;
  showTokens?: boolean;
  showRequests?: boolean;
}

export default function UsageTrendChart({
  data,
  title = "Usage Trend",
  height = 300,
  showCost = true,
  showTokens = true,
  showRequests = true
}: UsageTrendChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || !data || data.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = height;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Calculate dimensions
    const padding = 40;
    const chartWidth = canvas.width - padding * 2;
    const chartHeight = canvas.height - padding * 2;

    // Find max values
    const maxRequests = Math.max(...data.map(d => d.requests));
    const maxCost = Math.max(...data.map(d => d.cost));
    const maxTokens = Math.max(...data.map(d => d.tokens));

    // Draw axes
    ctx.strokeStyle = '#E5E7EB';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, canvas.height - padding);
    ctx.lineTo(canvas.width - padding, canvas.height - padding);
    ctx.stroke();

    // Draw grid lines
    ctx.strokeStyle = '#F3F4F6';
    ctx.setLineDash([5, 5]);
    for (let i = 0; i <= 5; i++) {
      const y = padding + (chartHeight / 5) * i;
      ctx.beginPath();
      ctx.moveTo(padding, y);
      ctx.lineTo(canvas.width - padding, y);
      ctx.stroke();
    }
    ctx.setLineDash([]);

    // Helper function to draw a line
    const drawLine = (dataPoints: number[], maxValue: number, color: string, lineWidth: number = 2) => {
      if (dataPoints.length < 2) return;

      ctx.strokeStyle = color;
      ctx.lineWidth = lineWidth;
      ctx.beginPath();

      dataPoints.forEach((value, index) => {
        const x = padding + (chartWidth / (dataPoints.length - 1)) * index;
        const y = canvas.height - padding - (value / maxValue) * chartHeight;

        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });

      ctx.stroke();

      // Draw points
      dataPoints.forEach((value, index) => {
        const x = padding + (chartWidth / (dataPoints.length - 1)) * index;
        const y = canvas.height - padding - (value / maxValue) * chartHeight;

        ctx.fillStyle = '#FFFFFF';
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();
      });
    };

    // Draw data lines
    const metrics = [
      {
        data: data.map(d => d.requests),
        max: maxRequests,
        color: '#3B82F6',
        label: 'Requests'
      },
      {
        data: data.map(d => d.cost),
        max: maxCost,
        color: '#10B981',
        label: 'Cost ($)'
      },
      {
        data: data.map(d => d.tokens),
        max: maxTokens,
        color: '#F59E0B',
        label: 'Tokens'
      }
    ];

    let leftAxisPadding = 0;

    metrics.forEach((metric, index) => {
      const shouldShow =
        (metric.label === 'Requests' && showRequests) ||
        (metric.label === 'Cost ($)' && showCost) ||
        (metric.label === 'Tokens' && showTokens);

      if (!shouldShow) return;

      const axisIndex = metrics.slice(0, index + 1).filter(m => {
        const shouldShowMetric =
          (m.label === 'Requests' && showRequests) ||
          (m.label === 'Cost ($)' && showCost) ||
          (m.label === 'Tokens' && showTokens);
        return shouldShowMetric;
      }).length - 1;

      const axisOffset = axisIndex * 15;
      const adjustedPadding = padding + axisOffset;

      // Draw Y-axis for this metric
      ctx.strokeStyle = metric.color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(adjustedPadding, padding);
      ctx.lineTo(adjustedPadding, canvas.height - padding);
      ctx.stroke();

      // Draw Y-axis labels
      ctx.fillStyle = metric.color;
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'right';
      for (let i = 0; i <= 5; i++) {
        const y = padding + (chartHeight / 5) * i;
        const value = metric.max - (metric.max / 5) * i;
        const label = metric.label === 'Cost ($)'
          ? `$${value.toFixed(0)}`
          : value.toLocaleString();
        ctx.fillText(label, adjustedPadding - 5, y + 3);
      }

      // Draw line chart
      const adjustedWidth = chartWidth - axisOffset;
      const adjustedChartWidth = canvas.width - adjustedPadding - 15;
      drawLine(
        metric.data,
        metric.max,
        metric.color,
        metric.label === 'Requests' ? 3 : 2
      );
    });

    // Draw title
    if (title) {
      ctx.fillStyle = '#111827';
      ctx.font = 'bold 16px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(title, canvas.width / 2, 20);
    }

    // Draw X-axis labels (dates)
    ctx.fillStyle = '#6B7280';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';

    const labelInterval = Math.ceil(data.length / 6); // Show at most 6 labels
    data.forEach((point, index) => {
      if (index % labelInterval === 0 || index === data.length - 1) {
        const x = padding + (chartWidth / (data.length - 1)) * index;
        const date = new Date(point.date);
        const label = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        ctx.fillText(label, x, canvas.height - padding + 20);
      }
    });

    // Draw legend
    const legendY = 30;
    let legendX = canvas.width - 150;

    const legendItems = metrics.filter((m, index) => {
      const shouldShow =
        (m.label === 'Requests' && showRequests) ||
        (m.label === 'Cost ($)' && showCost) ||
        (m.label === 'Tokens' && showTokens);
      return shouldShow;
    });

    legendItems.forEach((metric, index) => {
      const y = legendY + index * 20;

      // Draw color line
      ctx.strokeStyle = metric.color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(legendX, y);
      ctx.lineTo(legendX + 20, y);
      ctx.stroke();

      // Draw point
      ctx.fillStyle = '#FFFFFF';
      ctx.strokeStyle = metric.color;
      ctx.beginPath();
      ctx.arc(legendX + 10, y, 3, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();

      // Draw label
      ctx.fillStyle = '#374151';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(metric.label, legendX + 30, y + 4);
    });

  }, [data, height, showCost, showTokens, showRequests]);

  return (
    <div className="w-full">
      <canvas
        ref={canvasRef}
        className="w-full border border-gray-200 rounded-lg bg-white"
        style={{ height: `${height}px` }}
      />
    </div>
  );
}