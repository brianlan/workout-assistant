import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import {
  getPlanStats,
  type PlanStats,
} from "../api/client";

const COLORS = [
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
  "#84cc16",
];

export default function StatsPage() {
  const [stats, setStats] = useState<PlanStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPlanStats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="py-12 text-center text-gray-500">Loading...</div>;
  if (!stats) return <div className="py-12 text-center text-gray-500">No stats available.</div>;

  const categoryData = Object.entries(stats.category_breakdown).map(
    ([name, value]) => ({ name, value }),
  );

  // Summary bar chart data
  const summaryData = [
    { name: "Completed", value: stats.completed_items },
    { name: "Remaining", value: stats.total_items - stats.completed_items },
  ];

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Statistics</h1>

      {/* Summary cards */}
      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4 text-center">
          <p className="text-2xl font-bold text-blue-600">{Math.round(stats.completion_rate)}%</p>
          <p className="text-sm text-gray-600">Completion Rate</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{stats.total_plans}</p>
          <p className="text-sm text-gray-600">Total Plans</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{stats.completed_items}</p>
          <p className="text-sm text-gray-600">Completed Items</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{stats.total_items}</p>
          <p className="text-sm text-gray-600">Total Items</p>
        </div>
      </div>

      {/* Charts */}
      {stats.total_items > 0 && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Completion bar chart */}
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <h2 className="mb-4 text-lg font-semibold text-gray-800">Completion Rate</h2>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={summaryData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Category breakdown pie chart */}
          {categoryData.length > 0 && (
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <h2 className="mb-4 text-lg font-semibold text-gray-800">Category Breakdown</h2>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) =>
                      `${name} (${(percent * 100).toFixed(0)}%)`
                    }
                    outerRadius={80}
                    dataKey="value"
                  >
                    {categoryData.map((_entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={COLORS[index % COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {stats.total_items === 0 && (
        <p className="py-8 text-center text-gray-500">
          Complete some plan items to see statistics.
        </p>
      )}
    </div>
  );
}
