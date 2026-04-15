import { useCallback, useEffect, useState } from "react";
import {
  generatePlan,
  getActivePlan,
  togglePlanItem,
  regeneratePlan,
  type PlanGenerateParams,
  type PlanRead,
  type PlanItemRead,
} from "../api/client";

export default function PlansPage() {
  const [plan, setPlan] = useState<PlanRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [showGenerate, setShowGenerate] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  // Generate form state
  const [planType, setPlanType] = useState("weekly");
  const [focusAreas, setFocusAreas] = useState("");
  const [daysPerWeek, setDaysPerWeek] = useState(3);
  const [durationWeeks, setDurationWeeks] = useState(1);

  const loadPlan = useCallback(async () => {
    try {
      const p = await getActivePlan();
      setPlan(p);
    } catch {
      // No active plan
      setPlan(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPlan();
  }, [loadPlan]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    try {
      const params: PlanGenerateParams = { plan_type: planType };
      if (focusAreas.trim()) params.focus_areas = focusAreas.split(",").map((s) => s.trim());
      if (daysPerWeek) params.days_per_week = daysPerWeek;
      if (durationWeeks) params.duration_weeks = durationWeeks;
      const newPlan = await generatePlan(params);
      setPlan(newPlan);
      setShowGenerate(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate plan");
    } finally {
      setGenerating(false);
    }
  };

  const handleToggle = async (item: PlanItemRead) => {
    try {
      const updated = await togglePlanItem(item.plan_id, item.id, !item.completed);
      if (plan) {
        setPlan({
          ...plan,
          items: plan.items.map((i) => (i.id === updated.id ? updated : i)),
        });
      }
    } catch {
      // ignore
    }
  };

  const handleRegenerate = async () => {
    if (!plan) return;
    setGenerating(true);
    setError("");
    try {
      const newPlan = await regeneratePlan(plan.id);
      setPlan(newPlan);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to regenerate plan");
    } finally {
      setGenerating(false);
    }
  };

  // Group items by day
  const itemsByDay = new Map<number, PlanItemRead[]>();
  if (plan) {
    for (const item of plan.items) {
      const day = item.day_position;
      if (!itemsByDay.has(day)) itemsByDay.set(day, []);
      itemsByDay.get(day)!.push(item);
    }
    for (const [, items] of itemsByDay) {
      items.sort((a, b) => a.order_position - b.order_position);
    }
  }

  const completedCount = plan?.items.filter((i) => i.completed).length ?? 0;
  const totalCount = plan?.items.length ?? 0;
  const pct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  if (loading) return <div className="py-12 text-center text-gray-500">Loading...</div>;

  if (!plan && !showGenerate) {
    return (
      <div className="py-12 text-center">
        <h1 className="mb-4 text-2xl font-bold text-gray-900">Workout Plans</h1>
        <p className="mb-6 text-gray-600">No active plan. Generate one to get started.</p>
        <button
          onClick={() => setShowGenerate(true)}
          className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Generate Plan
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">
          {plan ? plan.title : "Generate Plan"}
        </h1>
        {plan && (
          <button
            onClick={handleRegenerate}
            disabled={generating}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Regenerate
          </button>
        )}
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {showGenerate && !plan && (
        <div className="mx-auto max-w-md rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-bold">Plan Parameters</h2>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Plan Type</label>
              <select
                value={planType}
                onChange={(e) => setPlanType(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="single_session">Single Session</option>
                <option value="weekly">Weekly</option>
                <option value="multi_week">Multi-Week</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Focus Areas</label>
              <input
                type="text"
                value={focusAreas}
                onChange={(e) => setFocusAreas(e.target.value)}
                placeholder="legs, chest, back (comma separated)"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Days per Week</label>
              <input
                type="number"
                min={1}
                max={7}
                value={daysPerWeek}
                onChange={(e) => setDaysPerWeek(Number(e.target.value))}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Duration (weeks)</label>
              <input
                type="number"
                min={1}
                max={12}
                value={durationWeeks}
                onChange={(e) => setDurationWeeks(Number(e.target.value))}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {generating ? "Generating..." : "Generate Plan"}
            </button>
          </div>
        </div>
      )}

      {plan && (
        <>
          {/* Progress bar */}
          <div className="mb-6">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">
                {completedCount}/{totalCount} completed
              </span>
              <span className="font-medium">{pct}%</span>
            </div>
            <div className="mt-1 h-2 w-full rounded-full bg-gray-200">
              <div
                className="h-2 rounded-full bg-blue-600 transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>

          {/* Days */}
          <div className="space-y-6">
            {Array.from(itemsByDay.entries())
              .sort(([a], [b]) => a - b)
              .map(([day, items]) => (
                <div key={day}>
                  <h2 className="mb-2 text-lg font-semibold text-gray-800">
                    Day {day}
                  </h2>
                  <div className="space-y-2">
                    {items.map((item) => (
                      <PlanItemCard
                        key={item.id}
                        item={item}
                        onToggle={() => handleToggle(item)}
                      />
                    ))}
                  </div>
                </div>
              ))}
          </div>
        </>
      )}
    </div>
  );
}

function PlanItemCard({
  item,
  onToggle,
}: {
  item: PlanItemRead;
  onToggle: () => void;
}) {
  return (
    <div
      className={`flex items-center gap-3 rounded-lg border p-3 ${
        item.completed ? "border-green-200 bg-green-50" : "border-gray-200 bg-white"
      } ${item.video_deleted ? "opacity-60" : ""}`}
    >
      <input
        type="checkbox"
        checked={item.completed}
        onChange={onToggle}
        className="h-4 w-4 rounded border-gray-300 text-blue-600"
      />
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium ${item.completed ? "line-through text-gray-500" : "text-gray-900"}`}>
          {item.video_deleted ? "Video unavailable" : (item.video_title ?? `Video #${item.video_id}`)}
        </p>
        {item.completed && item.completed_at && (
          <p className="text-xs text-gray-500">
            Completed {new Date(item.completed_at).toLocaleDateString()}
          </p>
        )}
      </div>
    </div>
  );
}
