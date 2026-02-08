import type { StatusUpdate } from '../api/client';

interface Props {
  updates: StatusUpdate[];
}

const TYPE_COLORS: Record<string, string> = {
  progress: 'text-blue-400',
  blocker: 'text-red-400',
  milestone: 'text-green-400',
  reminder: 'text-yellow-400',
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'now';
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}

export default function CompactFeed({ updates }: Props) {
  if (!updates.length) {
    return <div className="text-white/20 text-xs py-2">No updates</div>;
  }

  return (
    <div>
      {updates.map((u) => (
        <div
          key={u.id}
          className="flex items-center gap-2 text-xs leading-[24px] text-white/50 overflow-hidden"
        >
          {u.project_name && (
            <span
              className="font-medium text-white/70 shrink-0"
              style={{ color: u.project_color || undefined }}
            >
              [{u.project_name}]
            </span>
          )}
          <span className={`shrink-0 ${TYPE_COLORS[u.update_type] || 'text-white/40'}`}>
            {u.update_type}
          </span>
          <span className="truncate text-white/60">
            &ldquo;{u.content}&rdquo;
          </span>
          <span className="shrink-0 text-white/25 ml-auto">{u.author}</span>
          <span className="shrink-0 text-white/20 mono">{timeAgo(u.created_at)}</span>
        </div>
      ))}
    </div>
  );
}
