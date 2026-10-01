import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

export interface Violation {
  id: number;
  violation_id: string;
  violation_type: string;
  plate_text: string | null;
  confidence: number;
  device_id: string;
  latitude: number | null;
  longitude: number | null;
  timestamp: string;
  snapshot_path: string | null;
  video_path: string | null;
}

export interface DashboardStats {
  total_violations: number;
  no_helmet_count: number;
  triple_riding_count: number;
  unique_plates: number;
  violations_by_day: Record<string, number>;
  violations_by_type: Record<string, number>;
}

export const api = axios.create({ baseURL: API_BASE });

export async function fetchViolations(limit = 50) {
  const { data } = await api.get("/violations", { params: { limit } });
  return data;
}

export async function searchByPlate(plate: string) {
  const { data } = await api.get("/violations/search", { params: { plate } });
  return data;
}

export async function fetchStats(): Promise<DashboardStats> {
  const { data } = await api.get("/dashboard/stats");
  return data;
}

export function evidenceUrl(violationId: string, type: "snapshot" | "video") {
  return `${API_BASE}/violations/${violationId}/evidence/${type}`;
}
