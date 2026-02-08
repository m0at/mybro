import { useEffect, useState } from 'react';
import SystemStatusStrip from '../components/SystemStatusStrip';
import ProjectTable from '../components/ProjectTable';
import CompactFeed from '../components/CompactFeed';
import {
  getFullDashboard,
  type FullDashboardResponse,
} from '../api/client';

export default function Dashboard() {
  const [data, setData] = useState<FullDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try {
      const d = await getFullDashboard();
      setData(d);
    } catch (err) {
      console.error('Dashboard refresh failed:', err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 10_000);
    return () => clearInterval(interval);
  }, []);

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-64 text-white/30 text-sm mono">
        Loading...
      </div>
    );
  }

  return (
    <div className="-m-3">
      <SystemStatusStrip
        system={data.system}
        time={data.time}
        projectCount={data.projects.length}
      />
      <div className="p-3">
        <ProjectTable projects={data.projects} />
        <div className="mt-4">
          <h3 className="text-xs font-medium text-white/30 uppercase tracking-wider mb-1">Feed</h3>
          <CompactFeed updates={data.feed} />
        </div>
      </div>
    </div>
  );
}
