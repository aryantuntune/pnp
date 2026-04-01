"use client";

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface RevenueData {
  period: string;
  total_revenue: number;
  ticket_count?: number;
}

interface RevenueChartProps {
  data: RevenueData[];
}

export default function RevenueChart({ data }: RevenueChartProps) {
  const hasCount = data.some((d) => (d.ticket_count ?? 0) > 0);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="period" tick={{ fontSize: 11 }} />
        <YAxis
          yAxisId="revenue"
          tick={{ fontSize: 11 }}
          tickFormatter={(v: number) =>
            v >= 100000
              ? `₹${(v / 100000).toFixed(1)}L`
              : v >= 1000
              ? `₹${(v / 1000).toFixed(0)}k`
              : `₹${v}`
          }
        />
        {hasCount && (
          <YAxis
            yAxisId="count"
            orientation="right"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => `${v}`}
          />
        )}
        <Tooltip
          formatter={(value: number | undefined, name: string | undefined) => {
            const v = value ?? 0;
            if (name === "Tickets") return [v.toLocaleString("en-IN"), "Tickets"];
            return [
              `₹${v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
              "Revenue",
            ] as [string, string];
          }}
        />
        <Legend />
        <Bar
          yAxisId="revenue"
          dataKey="total_revenue"
          name="Revenue"
          fill="#3b82f6"
          radius={[4, 4, 0, 0]}
        />
        {hasCount && (
          <Line
            yAxisId="count"
            dataKey="ticket_count"
            name="Tickets"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
