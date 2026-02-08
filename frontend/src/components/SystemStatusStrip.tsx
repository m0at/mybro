import { useEffect, useState } from 'react';
import type { SystemSummary, TimeSummary } from '../api/client';
import { takeSnapshot, scanSessions, scoreAll } from '../api/client';

interface Props {
  system: SystemSummary;
  time: TimeSummary;
  projectCount: number;
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export default function SystemStatusStrip({ system, time, projectCount }: Props) {
  const [clock, setClock] = useState(new Date().toLocaleTimeString('en-US', { hour12: false }));

  useEffect(() => {
    const t = setInterval(() => {
      setClock(new Date().toLocaleTimeString('en-US', { hour12: false }));
    }, 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="status-strip">
      <span>{projectCount} projects</span>
      <span className="text-white/15">|</span>
      <span>{system.server_count} servers</span>
      <span className="text-white/15">|</span>
      <span>{system.script_count} scripts</span>
      <span className="text-white/15">|</span>
      <span>{system.claude_count} claude</span>
      <span className="text-white/15">|</span>
      <span>{system.droplet_count} droplets</span>
      <span className="text-white/15">|</span>
      <span>{formatDuration(time.total_active_s)} today</span>
      <span className="text-white/15">|</span>
      <span>{clock}</span>
      <span className="ml-auto flex gap-3">
        <button
          onClick={() => scanSessions().then(() => scoreAll())}
          className="text-white/25 hover:text-white/60 transition-colors"
        >
          scan
        </button>
        <button
          onClick={() => takeSnapshot()}
          className="text-white/25 hover:text-white/60 transition-colors"
        >
          snapshot
        </button>
      </span>
    </div>
  );
}
