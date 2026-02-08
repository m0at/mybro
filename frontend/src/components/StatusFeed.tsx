import type { StatusUpdate } from '../api/client';

interface Props {
  updates: StatusUpdate[];
}

const TYPE_COLORS: Record<string, string> = {
  progress: 'bg-blue-500/20 text-blue-400',
  blocker: 'bg-red-500/20 text-red-400',
  milestone: 'bg-green-500/20 text-green-400',
  reminder: 'bg-yellow-500/20 text-yellow-400',
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export default function StatusFeed({ updates }: Props) {
  if (!updates.length) {
    return (
      <div className="card text-center text-white/30 text-sm py-8">
        No status updates yet
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {updates.map((u) => (
        <div key={u.id} className="card flex items-start gap-3 py-3">
          <div
            className="w-1 rounded-full self-stretch mt-0.5"
            style={{ backgroundColor: u.project_color || '#667eea' }}
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              {u.project_name && (
                <span className="text-xs font-medium text-white/70">
                  {u.project_name}
                </span>
              )}
              <span className={`badge ${TYPE_COLORS[u.update_type] || TYPE_COLORS.progress}`}>
                {u.update_type}
              </span>
              <span className="badge bg-white/5 text-white/40">
                {u.author}
              </span>
            </div>
            <p className="text-sm text-white/80 leading-relaxed">{u.content}</p>
          </div>
          <span className="text-[0.65rem] text-white/30 whitespace-nowrap">
            {timeAgo(u.created_at)}
          </span>
        </div>
      ))}
    </div>
  );
}
