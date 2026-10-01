import { useEffect, useState } from "react";
import Analytics from "./components/Analytics";
import LiveCamera from "./components/LiveCamera";
import SearchBar from "./components/SearchBar";
import ViolationHistory from "./components/ViolationHistory";
import ViolationMap from "./components/ViolationMap";
import { DashboardStats, Violation, fetchStats, fetchViolations } from "./services/api";

export default function App() {
  const [violations, setViolations] = useState<Violation[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [violationsRes, statsRes] = await Promise.all([
        fetchViolations(100),
        fetchStats(),
      ]);
      setViolations(violationsRes.items);
      setStats(statsRes);
      setError(null);
    } catch (err) {
      setError("Failed to load dashboard data. Is the API running?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const exportReport = () => {
    const blob = new Blob([JSON.stringify({ stats, violations }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `violation-report-${new Date().toISOString()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Smart Helmet Violation Dashboard</h1>
          <p>Edge AI traffic violation monitoring</p>
        </div>
        <button className="btn" onClick={exportReport}>
          Export Report
        </button>
      </header>

      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="loading">Loading...</div>}

      <SearchBar onResults={(items) => setViolations(items)} />

      <section className="grid stats-grid">
        <div className="card stat">
          <span>Total Violations</span>
          <strong>{stats?.total_violations ?? 0}</strong>
        </div>
        <div className="card stat">
          <span>No Helmet</span>
          <strong>{stats?.no_helmet_count ?? 0}</strong>
        </div>
        <div className="card stat">
          <span>Triple Riding</span>
          <strong>{stats?.triple_riding_count ?? 0}</strong>
        </div>
        <div className="card stat">
          <span>Unique Plates</span>
          <strong>{stats?.unique_plates ?? 0}</strong>
        </div>
      </section>

      <section className="grid main-grid">
        <LiveCamera />
        <Analytics stats={stats} />
      </section>

      <section className="grid map-grid">
        <ViolationMap violations={violations} />
        <ViolationHistory violations={violations} />
      </section>
    </div>
  );
}
