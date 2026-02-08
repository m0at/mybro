import { useEffect, useState } from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

interface TimeData {
  date: string;
  project_time: Record<string, number>;
  total_active_s: number;
  total_afk_s: number;
  afk_periods: Array<{
    started_at: number;
    ended_at: number | null;
    duration_s: number | null;
    claude_active: boolean;
  }>;
  activity_windows: Array<{
    project: string | null;
    started_at: number;
    ended_at: number | null;
  }>;
}

const PROJECT_COLORS = [
  '#667eea', '#764ba2', '#4ade80', '#f59e0b', '#f87171',
  '#22d3ee', '#a78bfa', '#fb923c', '#34d399', '#f472b6',
  '#60a5fa', '#fbbf24', '#a3e635', '#e879f9', '#2dd4bf',
];

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export default function TimeTracking() {
  const [data, setData] = useState<TimeData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/time/today')
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-white/30 text-center py-12">Loading...</div>;
  }

  if (!data || (data.total_active_s === 0 && data.afk_periods.length === 0)) {
    return (
      <div>
        <h2 className="text-xl font-bold mb-4">Time Tracking</h2>
        <div className="card text-center text-white/30 py-12">
          <p className="text-lg mb-2">No activity data yet</p>
          <p className="text-sm">
            Start the tracker daemon to begin collecting data:
          </p>
          <code className="block mt-3 text-white/50 text-xs">
            python -m tracker.main
          </code>
          <p className="text-xs mt-2 text-white/20">
            Or install launchd agents: ./launchd/install.sh
          </p>
        </div>
      </div>
    );
  }

  const projects = Object.entries(data.project_time).sort((a, b) => b[1] - a[1]);
  const colorMap: Record<string, string> = {};
  projects.forEach(([name], i) => {
    colorMap[name] = PROJECT_COLORS[i % PROJECT_COLORS.length];
  });

  const chartData = {
    labels: projects.map(([name]) => name),
    datasets: [
      {
        data: projects.map(([, secs]) => Math.round(secs / 60)),
        backgroundColor: projects.map(([name]) => colorMap[name]),
        borderRadius: 4,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 11 } }, grid: { display: false } },
      y: {
        ticks: { color: 'rgba(255,255,255,0.3)', callback: (v: number) => `${v}m` },
        grid: { color: 'rgba(255,255,255,0.05)' },
      },
    },
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Time Tracking</h2>
        <span className="text-sm text-white/40">{data.date}</span>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="card text-center">
          <div className="text-2xl font-bold">{formatDuration(data.total_active_s)}</div>
          <div className="text-xs text-white/40 mt-1">Active Time</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold">{formatDuration(data.total_afk_s)}</div>
          <div className="text-xs text-white/40 mt-1">AFK Time</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold">{projects.length}</div>
          <div className="text-xs text-white/40 mt-1">Projects Worked</div>
        </div>
      </div>

      {/* Time per project chart */}
      <div className="card mb-6">
        <h3 className="text-sm font-medium text-white/50 mb-3">Minutes per Project</h3>
        <div className="h-64">
          <Bar data={chartData} options={chartOptions as any} />
        </div>
      </div>

      {/* Project breakdown */}
      <div className="card mb-6">
        <h3 className="text-sm font-medium text-white/50 mb-3">Breakdown</h3>
        <div className="space-y-2">
          {projects.map(([name, secs]) => {
            const pct = data.total_active_s > 0 ? (secs / data.total_active_s) * 100 : 0;
            return (
              <div key={name} className="flex items-center gap-3">
                <span
                  className="w-3 h-3 rounded-full shrink-0"
                  style={{ backgroundColor: colorMap[name] }}
                />
                <span className="text-sm flex-1">{name}</span>
                <span className="text-xs text-white/40">{formatDuration(secs)}</span>
                <div className="w-32 h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${pct}%`, backgroundColor: colorMap[name] }}
                  />
                </div>
                <span className="text-xs text-white/30 w-10 text-right">
                  {Math.round(pct)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* AFK periods */}
      {data.afk_periods.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-medium text-white/50 mb-3">
            AFK Periods ({data.afk_periods.length})
          </h3>
          <div className="space-y-1">
            {data.afk_periods.map((p, i) => (
              <div key={i} className="flex items-center justify-between text-xs text-white/40 py-1">
                <span>
                  {new Date(p.started_at * 1000).toLocaleTimeString()} —{' '}
                  {p.ended_at ? new Date(p.ended_at * 1000).toLocaleTimeString() : 'ongoing'}
                </span>
                <div className="flex items-center gap-2">
                  {p.claude_active && (
                    <span className="badge bg-purple-500/20 text-purple-400">Claude active</span>
                  )}
                  <span>{p.duration_s ? formatDuration(p.duration_s) : '...'}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
