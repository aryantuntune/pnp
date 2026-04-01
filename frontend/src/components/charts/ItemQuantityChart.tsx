"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

interface ItemData {
  item_name: string;
  is_vehicle: boolean;
  total_revenue: number;
  total_quantity: number;
}

interface ItemQuantityChartProps {
  data: ItemData[];
}

const VEHICLE_COLOR = "#3b82f6";
const PASSENGER_COLOR = "#22c55e";

export default function ItemQuantityChart({ data }: ItemQuantityChartProps) {
  const sorted = useMemo(
    () => [...data].sort((a, b) => b.total_quantity - a.total_quantity).slice(0, 8),
    [data]
  );

  if (sorted.length === 0) {
    return (
      <div className="flex items-center justify-center h-[220px] text-sm text-muted-foreground">
        No data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={sorted} layout="vertical" margin={{ left: 0, right: 16 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11 }} />
        <YAxis
          type="category"
          dataKey="item_name"
          tick={{ fontSize: 11 }}
          width={110}
        />
        <Tooltip
          formatter={(value: number | undefined) =>
            [(value ?? 0).toLocaleString("en-IN"), "Quantity"] as [string, string]
          }
          labelFormatter={(label) => String(label ?? "")}
        />
        <Bar dataKey="total_quantity" radius={[0, 4, 4, 0]}>
          {sorted.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.is_vehicle ? VEHICLE_COLOR : PASSENGER_COLOR}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
