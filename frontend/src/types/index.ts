export interface Category {
  id: number;
  name: string;
  created_at: string;
}

export interface Video {
  id: number;
  title: string;
  description: string | null;
  category_id: number;
  difficulty: string | null;
  muscle_groups: string | null;
  duration: number | null;
  format: string | null;
  file_size: number | null;
  thumbnail_path: string | null;
  file_path: string;
  source_url: string | null;
  status: string;
  imported_at: string;
}

export interface Plan {
  id: number;
  title: string;
  plan_type: string;
  parameters: string;
  created_at: string;
}

export interface PlanItem {
  id: number;
  plan_id: number;
  video_id: number | null;
  day_position: number;
  order_position: number;
  completed: boolean;
  completed_at: string | null;
}

export interface Settings {
  base_url: string;
  api_key: string;
  model_name: string;
}

export type Difficulty = "beginner" | "intermediate" | "advanced";

export type PlanType = "single_session" | "weekly" | "multi_week";

