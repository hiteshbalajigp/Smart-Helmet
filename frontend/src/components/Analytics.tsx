import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { DashboardStats } from "../services/api";

interface Props {
  stats: DashboardStats | null;
}

export default function Analytics({ stats }: Props) {
  const byDay = Object.entries(stats?.violations_by_day ?? {}).map(([day, count]) => ({
    day,
    count,
  }));
  const byType = Object.entries(stats?.violations_by_type ?? {}).map(([type, count]) => ({
    type,
    count,
  }));

  return (
    <div className="card">
      <h2>Analytics</h2>
      <div className="charts">
        <div>
          <h3>Violations by Day</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={byDay}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#2563eb" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div>
          <h3>Violations by Type</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={byType}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="type" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#dc2626" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
