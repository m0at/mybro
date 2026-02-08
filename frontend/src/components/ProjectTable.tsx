import { useState } from 'react';
import type { DashboardProjectFull } from '../api/client';

interface Props {
  projects: DashboardProjectFull[];
}

function timeAgo(ts: number | null): string {
  if (!ts) return '—';
  const diff = Date.now() / 1000 - ts;
  const mins = Math.floor(diff / 60);
  if (mins < 1) return 'now';
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d`;
  return `${Math.floor(days / 30)}mo`;
}

function isRecent(ts: number | null, thresholdS: number): boolean {
  if (!ts) return false;
  return (Date.now() / 1000 - ts) < thresholdS;
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  in_progress: { label: 'ip', color: '#60a5fa' },
  todo: { label: 'td', color: '#fbbf24' },
  backlog: { label: 'bl', color: '#9ca3af' },
  blocked: { label: 'bk', color: '#f87171' },
  review: { label: 'rv', color: '#a78bfa' },
};

const HEALTH_COLORS: Record<string, string> = {
  hot: 'text-orange-400',
  active: 'text-green-400',
  stale: 'text-yellow-500/60',
  dead: 'text-white/20',
  unknown: 'text-white/15',
};

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return String(n);
}

function ProjectRow({ data }: { data: DashboardProjectFull }) {
  const { project, git, loc, tickets, servers, scripts, claude, droplets, health, sessions } = data;

  const hasServer = servers.length > 0;
  const hasClaude = claude.length > 0;
  const isRecentCommit = isRecent(git.commit_ts, 3600);
  const isDimBranch = ['main', 'master'].includes(git.branch);

  // LOC 3-day totals
  const added = loc.reduce((a, l) => a + l.lines_added, 0);
  const removed = loc.reduce((a, l) => a + l.lines_removed, 0);

  // Ticket summary
  const ticketParts = Object.entries(tickets)
    .map(([status, count]) => {
      const info = STATUS_LABELS[status];
      if (!info) return null;
      return { ...info, count };
    })
    .filter(Boolean) as { label: string; color: string; count: number }[];

  const githubUrl = git.github_url || project.github_url;

  return (
    <tr className={isRecentCommit ? 'recent-glow' : ''}>
      {/* Color dot */}
      <td className="w-4 pr-0">
        <span
          className={`inline-block w-2 h-2 rounded-full ${hasServer ? 'pulse-dot' : ''}`}
          style={{ backgroundColor: project.color }}
        />
      </td>

      {/* Name */}
      <td className="font-semibold text-white/90">
        {githubUrl ? (
          <a
            href={githubUrl}
            target="_blank"
            rel="noopener"
            className="hover:text-[var(--accent)] transition-colors"
          >
            {project.name}
          </a>
        ) : (
          project.name
        )}
      </td>

      {/* Branch */}
      <td className={`mono ${isDimBranch ? 'text-white/25' : 'text-white/60'}`}>
        {git.branch || '—'}
      </td>

      {/* Last Commit */}
      <td className="max-w-[240px]">
        <span className="text-white/50 truncate block" title={git.commit_message}>
          {git.commit_message ? git.commit_message.slice(0, 40) : '—'}
          {git.commit_message && git.commit_message.length > 40 ? '…' : ''}
        </span>
      </td>

      {/* Time ago */}
      <td className="mono text-white/30 text-right">
        {timeAgo(git.commit_ts)}
      </td>

      {/* Uncommitted */}
      <td className={`mono text-right ${git.uncommitted > 0 ? 'text-yellow-400' : 'text-white/20'}`}>
        {git.uncommitted || '—'}
      </td>

      {/* LOC */}
      <td className="mono text-right">
        {added > 0 || removed > 0 ? (
          <>
            <span className="text-green-400">+{added}</span>
            <span className="text-white/15 mx-0.5">/</span>
            <span className="text-red-400">-{removed}</span>
          </>
        ) : (
          <span className="text-white/15">—</span>
        )}
      </td>

      {/* Tickets */}
      <td>
        {ticketParts.length > 0 ? (
          <span className="flex gap-1.5">
            {ticketParts.map((t) => (
              <span key={t.label} className="mono" style={{ color: t.color }}>
                {t.count}{t.label}
              </span>
            ))}
          </span>
        ) : (
          <span className="text-white/15">—</span>
        )}
      </td>

      {/* Infra */}
      <td>
        <span className="flex gap-1">
          {servers.map((s) => (
            <span
              key={s.port}
              className="mono text-green-400/80 text-[0.7rem]"
              title={`${s.command} :${s.port}`}
            >
              :{s.port}
            </span>
          ))}
          {droplets.map((d) => (
            <span
              key={d.droplet_id}
              className={`text-[0.65rem] font-semibold ${d.status === 'active' ? 'text-green-400/70' : 'text-red-400/70'}`}
              title={`${d.name} (${d.region})`}
            >
              DO
            </span>
          ))}
          {servers.length === 0 && droplets.length === 0 && (
            <span className="text-white/15">—</span>
          )}
        </span>
      </td>

      {/* Procs */}
      <td>
        <span className="flex gap-1.5">
          {hasClaude && (
            <span className="text-purple-400/80 mono text-[0.7rem]" title="Claude Code">
              C{claude.length > 1 ? claude.length : ''}
            </span>
          )}
          {scripts.length > 0 && (
            <span className="text-blue-400/70 mono text-[0.7rem]" title="Scripts">
              S{scripts.length > 1 ? scripts.length : ''}
            </span>
          )}
          {!hasClaude && scripts.length === 0 && (
            <span className="text-white/15">—</span>
          )}
        </span>
      </td>

      {/* Sessions */}
      <td className="mono text-right">
        {sessions.total > 0 ? (
          <span className="text-purple-300/70" title={`${sessions.total} total, ${formatTokens(sessions.total_tokens)} tokens`}>
            {sessions.last_7d > 0 ? `${sessions.last_7d}w` : sessions.total}
          </span>
        ) : (
          <span className="text-white/15">—</span>
        )}
      </td>

      {/* Health */}
      <td className="text-center">
        <span
          className={`mono text-[0.7rem] font-semibold ${HEALTH_COLORS[health.label]}`}
          title={`Score: ${health.score}/100`}
        >
          {health.label !== 'unknown' ? health.score : '—'}
        </span>
      </td>
    </tr>
  );
}

export default function ProjectTable({ projects }: Props) {
  const [showInactive, setShowInactive] = useState(false);

  const SEVEN_DAYS = 7 * 24 * 3600;
  const now = Date.now() / 1000;

  const active = projects.filter((p) => {
    const commitAge = p.git.commit_ts ? now - p.git.commit_ts : Infinity;
    return commitAge < SEVEN_DAYS || p.servers.length > 0 || p.claude.length > 0;
  });

  const inactive = projects.filter((p) => {
    const commitAge = p.git.commit_ts ? now - p.git.commit_ts : Infinity;
    return commitAge >= SEVEN_DAYS && p.servers.length === 0 && p.claude.length === 0;
  });

  return (
    <div>
      <table className="cc-table">
        <thead>
          <tr>
            <th className="w-4"></th>
            <th>Name</th>
            <th>Branch</th>
            <th>Last Commit</th>
            <th className="text-right">Ago</th>
            <th className="text-right">Chg</th>
            <th className="text-right">LOC (3d)</th>
            <th>Tickets</th>
            <th>Infra</th>
            <th>Procs</th>
            <th className="text-right">Sess</th>
            <th className="text-center">HP</th>
          </tr>
        </thead>
        <tbody>
          {active.map((p) => (
            <ProjectRow key={p.project.id} data={p} />
          ))}
        </tbody>
      </table>

      {inactive.length > 0 && (
        <div className="mt-2">
          <button
            onClick={() => setShowInactive(!showInactive)}
            className="text-xs text-white/25 hover:text-white/50 transition-colors py-1"
          >
            {showInactive ? '▾' : '▸'} {inactive.length} inactive
          </button>
          {showInactive && (
            <table className="cc-table opacity-50">
              <tbody>
                {inactive.map((p) => (
                  <ProjectRow key={p.project.id} data={p} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
