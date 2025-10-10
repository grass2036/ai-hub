'use client';

import { useEffect, useRef } from 'react';

interface CostData {
  category: string;
  cost: number;
  requests: number;
  color: string;
}

interface CostBreakdownProps {
  data: CostData[];
  title?: string;
  height?: number;
}

const DEFAULT_COLORS = [
  '#3B82F6', // blue
  '#10B981', // emerald
  '#F59E0B', // amber
  '#EF4444', // red
  '#8B5CF6', // violet
  '#EC4899', // pink
  '#14B8A6', // teal
  '#F97316', // orange
];

export default function CostBreakdown({ data, title = "Cost Breakdown", height = 300 }: CostBreakdownProps) {
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
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) - 40;

    // Calculate total cost
    const totalCost = data.reduce((sum, item) => sum + item.cost, 0);

    // Draw title
    if (title) {
      ctx.fillStyle = '#111827';
      ctx.font = 'bold 16px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(title, centerX, 20);
    }

    // Draw pie chart
    let currentAngle = -Math.PI / 2; // Start from top

    data.forEach((item, index) => {
      const sliceAngle = (item.cost / totalCost) * 2 * Math.PI;

      // Draw slice
      ctx.fillStyle = item.color || DEFAULT_COLORS[index % DEFAULT_COLORS.length];
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
      ctx.closePath();
      ctx.fill();

      // Draw border
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Calculate label position
      const labelAngle = currentAngle + sliceAngle / 2;
      const labelX = centerX + Math.cos(labelAngle) * (radius * 0.7);
      const labelY = centerY + Math.sin(labelAngle) * (radius * 0.7);

      // Draw percentage label
      const percentage = ((item.cost / totalCost) * 100).toFixed(1);
      if (percentage > 5) { // Only show label for slices > 5%
        ctx.fillStyle = '#FFFFFF';
        ctx.font = 'bold 14px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${percentage}%`, labelX, labelY);
      }

      currentAngle += sliceAngle;
    });

    // Draw legend
    const legendX = 20;
    let legendY = height - 120;

    ctx.font = '12px sans-serif';
    ctx.textAlign = 'left';

    data.forEach((item, index) => {
      // Draw color box
      ctx.fillStyle = item.color || DEFAULT_COLORS[index % DEFAULT_COLORS.length];
      ctx.fillRect(legendX, legendY - 10, 12, 12);

      // Draw text
      ctx.fillStyle = '#374151';
      ctx.fillText(item.category, legendX + 20, legendY);

      // Draw cost and percentage
      const itemPercentage = ((item.cost / totalCost) * 100).toFixed(1);
      ctx.fillStyle = '#6B7280';
      ctx.fillText(`$${item.cost.toFixed(2)} (${itemPercentage}%)`, legendX + 20, legendY + 15);

      legendY += 35;
    });

    // Draw center circle (donut chart effect)
    ctx.fillStyle = '#FFFFFF';
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.3, 0, 2 * Math.PI);
    ctx.fill();

    // Draw total cost in center
    ctx.fillStyle = '#111827';
    ctx.font = 'bold 18px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`$${totalCost.toFixed(2)}`, centerX, centerY);

    ctx.font = '12px sans-serif';
    ctx.fillStyle = '#6B7280';
    ctx.fillText('Total Cost', centerX, centerY + 20);

  }, [data, height]);

  // Process data to ensure colors
  const processedData = data.map((item, index) => ({
    ...item,
    color: item.color || DEFAULT_COLORS[index % DEFAULT_COLORS.length]
  }));

  return (
    <div className="w-full">
      <div className="bg-white p-6 rounded-lg shadow">
        <canvas
          ref={canvasRef}
          className="w-full"
          style={{ height: `${height}px` }}
        />

        {/* Detailed breakdown table */}
        <div className="mt-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Detailed Breakdown</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Cost
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Requests
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    % of Total
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {processedData.map((item) => {
                  const percentage = ((item.cost / processedData.reduce((sum, d) => sum + d.cost, 0)) * 100);
                  return (
                    <tr key={item.category}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div
                            className="w-3 h-3 rounded-full mr-3"
                            style={{ backgroundColor: item.color }}
                          />
                          <span className="text-sm font-medium text-gray-900">
                            {item.category}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        ${item.cost.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {item.requests.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {percentage.toFixed(1)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}