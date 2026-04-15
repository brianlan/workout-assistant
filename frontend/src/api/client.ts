import type { Category, Video, Settings } from "../types";

const API_BASE = "/api";

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

// Categories
export async function getCategories(): Promise<Category[]> {
  return request<Category[]>("/categories");
}

export async function createCategory(name: string): Promise<Category> {
  return request<Category>("/categories", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export async function updateCategory(
  id: number,
  name: string,
): Promise<Category> {
  return request<Category>(`/categories/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export async function deleteCategory(
  id: number,
  reassignTo?: number,
): Promise<void> {
  const params = reassignTo ? `?reassign_to=${reassignTo}` : "";
  const response = await fetch(`${API_BASE}/categories/${id}${params}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
}

// Videos
export async function getVideos(params?: {
  category_id?: number;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<Video[]> {
  const searchParams = new URLSearchParams();
  if (params?.category_id) searchParams.set("category_id", String(params.category_id));
  if (params?.search) searchParams.set("search", params.search);
  if (params?.page) searchParams.set("page", String(params.page));
  const qs = searchParams.toString();
  return request<Video[]>(`/videos${qs ? `?${qs}` : ""}`);
}

export async function updateVideo(
  id: number,
  data: Partial<Pick<Video, "title" | "description" | "difficulty" | "muscle_groups" | "category_id">>,
): Promise<Video> {
  return request<Video>(`/videos/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteVideo(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/videos/${id}`, { method: "DELETE" });
  if (!response.ok && response.status !== 204) {
    throw new Error(`Failed to delete video: ${response.statusText}`);
  }
}

export async function uploadVideo(
  file: File,
  categoryId: number,
  metadata?: {
    title?: string;
    description?: string;
    difficulty?: string;
    muscle_groups?: string;
  },
): Promise<Video> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("category_id", String(categoryId));
  if (metadata?.title) formData.append("title", metadata.title);
  if (metadata?.description) formData.append("description", metadata.description);
  if (metadata?.difficulty) formData.append("difficulty", metadata.difficulty);
  if (metadata?.muscle_groups) formData.append("muscle_groups", metadata.muscle_groups);

  const response = await fetch(`${API_BASE}/videos/upload`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

export async function importVideoUrl(
  url: string,
  categoryId: number,
  metadata?: {
    title?: string;
    description?: string;
    difficulty?: string;
    muscle_groups?: string;
  },
): Promise<Video> {
  return request<Video>("/videos/import-url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url,
      category_id: categoryId,
      ...metadata,
    }),
  });
}

export function getVideoStreamUrl(id: number): string {
  return `${API_BASE}/videos/${id}/stream`;
}

export function getVideoThumbnailUrl(id: number): string {
  return `${API_BASE}/videos/${id}/thumbnail`;
}

// Plans
export interface PlanGenerateParams {
  plan_type: string;
  focus_areas?: string[];
  days_per_week?: number;
  duration_weeks?: number;
}

export interface PlanRead {
  id: number;
  title: string;
  plan_type: string;
  parameters: string;
  created_at: string;
  items: PlanItemRead[];
}

export interface PlanItemRead {
  id: number;
  plan_id: number;
  video_id: number | null;
  day_position: number;
  order_position: number;
  completed: boolean;
  completed_at: string | null;
  video_title: string | null;
  video_deleted: boolean;
}

export interface PlanHistoryItem {
  id: number;
  title: string;
  plan_type: string;
  created_at: string;
  total_items: number;
  completed_items: number;
  completion_pct: number;
}

export interface PlanStats {
  completion_rate: number;
  total_plans: number;
  total_items: number;
  completed_items: number;
  category_breakdown: Record<string, number>;
}

export async function generatePlan(params: PlanGenerateParams): Promise<PlanRead> {
  return request<PlanRead>("/plans/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export async function getPlans(): Promise<PlanRead[]> {
  return request<PlanRead[]>("/plans");
}

export async function getPlan(id: number): Promise<PlanRead> {
  return request<PlanRead>(`/plans/${id}`);
}

export async function getActivePlan(): Promise<PlanRead> {
  return request<PlanRead>("/plans/active");
}

export async function togglePlanItem(
  planId: number,
  itemId: number,
  completed: boolean,
): Promise<PlanItemRead> {
  return request<PlanItemRead>(`/plans/${planId}/items/${itemId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ completed }),
  });
}

export async function regeneratePlan(planId: number): Promise<PlanRead> {
  return request<PlanRead>(`/plans/${planId}/regenerate`, {
    method: "POST",
  });
}

export async function getPlanHistory(): Promise<PlanHistoryItem[]> {
  return request<PlanHistoryItem[]>("/plans/history");
}

export async function getPlanStats(): Promise<PlanStats> {
  return request<PlanStats>("/plans/stats");
}

// Settings
export interface SettingsRead {
  base_url: string;
  api_key: string;
  model_name: string;
  api_key_masked: string;
}

export async function getSettings(): Promise<SettingsRead> {
  return request<SettingsRead>("/settings");
}

export async function updateSettings(data: Partial<Settings>): Promise<SettingsRead> {
  return request<SettingsRead>("/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
