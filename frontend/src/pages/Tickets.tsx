import { useEffect, useState } from 'react';
import { getTickets, updateTicket, type Ticket } from '../api/client';

const COLUMNS = [
  { key: 'backlog', label: 'Backlog', color: '#64748b' },
  { key: 'todo', label: 'Todo', color: '#3b82f6' },
  { key: 'in_progress', label: 'In Progress', color: '#f59e0b' },
  { key: 'done', label: 'Done', color: '#22c55e' },
];

const PRIORITY_COLORS: Record<string, string> = {
  urgent: 'bg-red-500/20 text-red-400',
  high: 'bg-orange-500/20 text-orange-400',
  medium: 'bg-blue-500/20 text-blue-400',
  low: 'bg-white/5 text-white/40',
};

export default function Tickets() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [dragging, setDragging] = useState<number | null>(null);

  async function refresh() {
    const data = await getTickets({ limit: '200' });
    setTickets(data.tickets);
  }

  useEffect(() => {
    refresh();
  }, []);

  function handleDragStart(e: React.DragEvent, ticketId: number) {
    setDragging(ticketId);
    e.dataTransfer.effectAllowed = 'move';
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }

  async function handleDrop(e: React.DragEvent, status: string) {
    e.preventDefault();
    if (dragging === null) return;
    await updateTicket(dragging, { status });
    setDragging(null);
    refresh();
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Tickets</h2>
        <span className="text-sm text-white/40">{tickets.length} total</span>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {COLUMNS.map((col) => {
          const colTickets = tickets.filter((t) => t.status === col.key);
          return (
            <div
              key={col.key}
              className="min-h-[60vh]"
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, col.key)}
            >
              <div className="flex items-center gap-2 mb-3 px-1">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: col.color }}
                />
                <span className="text-sm font-medium text-white/70">
                  {col.label}
                </span>
                <span className="text-xs text-white/30">{colTickets.length}</span>
              </div>

              <div className="space-y-2">
                {colTickets.map((t) => (
                  <div
                    key={t.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, t.id)}
                    className={`card cursor-grab active:cursor-grabbing py-3 ${
                      dragging === t.id ? 'opacity-50' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <span className="text-sm font-medium leading-snug">
                        {t.title}
                      </span>
                      <span className="text-[0.6rem] text-white/30 whitespace-nowrap">
                        #{t.id}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className={`badge ${PRIORITY_COLORS[t.priority] || ''}`}>
                        {t.priority}
                      </span>
                      {t.project_name && (
                        <span className="badge bg-white/5 text-white/40">
                          {t.project_name}
                        </span>
                      )}
                      <span className="badge bg-white/5 text-white/30">
                        {t.assignee}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
