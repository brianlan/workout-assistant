import { useEffect, useState } from "react";
import { getPlanHistory, type PlanHistoryItem } from "../api/client";

export default function PlanHistoryPage() {
  const [history, setHistory] = useState<PlanHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPlanHistory()
      .then(setHistory)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="py-12 text-center text-gray-500">Loading...</div>;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Plan History</h1>

      {history.length === 0 ? (
        <p className="py-12 text-center text-gray-500">No plans yet.</p>
      ) : (
        <div className="space-y-3">
          {history.map((plan) => (
            <div
              key={plan.id}
              className="rounded-lg border border-gray-200 bg-white p-4"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">{plan.title}</h3>
                  <p className="text-sm text-gray-500">
                    {plan.plan_type.replace("_", " ")} &middot;{" "}
                    {new Date(plan.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-lg font-bold text-blue-600">
                    {Math.round(plan.completion_pct)}%
                  </span>
                  <p className="text-xs text-gray-500">
                    {plan.completed_items}/{plan.total_items} items
                  </p>
                </div>
              </div>
              {/* Mini progress bar */}
              <div className="mt-2 h-1.5 w-full rounded-full bg-gray-200">
                <div
                  className="h-1.5 rounded-full bg-blue-600"
                  style={{ width: `${plan.completion_pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
