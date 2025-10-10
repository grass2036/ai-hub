'use client';

import { useEffect, useRef } from 'react';

interface BudgetData {
  date: string;
  cost: number;
  budget_limit: number;
  usage_percentage: number;
}

interface BudgetChartProps {
  data: BudgetData[];
  title?: string;
  height?: number;
  color?: string;
}

export default function BudgetChart({ data, title = "Budget Usage", height = 300, color = "#3B82F6" }: BudgetChartProps) {
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
    const maxCost = Math.max(...data.map(d => d.cost));
    const maxBudget = Math.max(...data.map(d => d.budget_limit));
    const maxValue = Math.max(maxCost, maxBudget);

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

      // Y-axis labels
      const value = maxValue - (maxValue / 5) * i;
      ctx.fillStyle = '#6B7280';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(`$${value.toFixed(0)}`, padding - 10, y + 4);
    }
    ctx.setLineDash([]);

    // Draw budget line (horizontal)
    if (data.length > 0 && data[0].budget_limit > 0) {
      const budgetY = canvas.height - padding - (data[0].budget_limit / maxValue) * chartHeight;
      ctx.strokeStyle = '#EF4444';
      ctx.lineWidth = 2;
      ctx.setLineDash([10, 5]);
      ctx.beginPath();
      ctx.moveTo(padding, budgetY);
      ctx.lineTo(canvas.width - padding, budgetY);
      ctx.stroke();
      ctx.setLineDash([]);

      // Budget label
      ctx.fillStyle = '#EF4444';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(`Budget: $${data[0].budget_limit.toFixed(2)}`, canvas.width - padding + 10, budgetY - 5);
    }

    // Draw area chart
    if (data.length > 1) {
      const gradient = ctx.createLinearGradient(0, padding, 0, canvas.height - padding);
      gradient.addColorStop(0, color + '40');
      gradient.addColorStop(1, color + '10');

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.moveTo(padding, canvas.height - padding);

      data.forEach((point, index) => {
        const x = padding + (chartWidth / (data.length - 1)) * index;
        const y = canvas.height - padding - (point.cost / maxValue) * chartHeight;

        if (index === 0) {
          ctx.lineTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });

      ctx.lineTo(canvas.width - padding, canvas.height - padding);
      ctx.closePath();
      ctx.fill();

      // Draw line
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      data.forEach((point, index) => {
        const x = padding + (chartWidth / (data.length - 1)) * index;
        const y = canvas.height - padding - (point.cost / maxValue) * chartHeight;

        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.stroke();

      // Draw points
      data.forEach((point, index) => {
        const x = padding + (chartWidth / (data.length - 1)) * index;
        const y = canvas.height - padding - (point.cost / maxValue) * chartHeight;

        ctx.fillStyle = '#FFFFFF';
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();
      });

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
    }

    // Draw title
    if (title) {
      ctx.fillStyle = '#111827';
      ctx.font = 'bold 16px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(title, canvas.width / 2, 20);
    }

    // Draw summary statistics
    const totalCost = data.reduce((sum, d) => sum + d.cost, 0);
    const avgCost = totalCost / data.length;
    const avgUsage = data.reduce((sum, d) => sum + d.usage_percentage, 0) / data.length;

    ctx.fillStyle = '#6B7280';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'left';

    ctx.fillText(`Total: $${totalCost.toFixed(2)}`, padding, height + 20);
    ctx.fillText(`Average: $${avgCost.toFixed(2)}`, padding + 150, height + 20);
    ctx.fillText(`Avg Usage: ${avgUsage.toFixed(1)}%`, padding + 300, height + 20);

  }, [data, height, color]);

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