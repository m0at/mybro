const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export interface Project {
  id: number;
  name: string;
  slug: string;
  repo_path: string | null;
  github_url: string | null;
  description: string | null;
  status: string;
  color: string;
  created_at: string;
  updated_at: string;
}

export interface LocSnapshot {
  date: string;
  lines_added: number;
  lines_removed: number;
  commit_count: number;
}

export interface DashboardProject {
  project: Project;
  loc: LocSnapshot[];
}

export interface Server {
  pid: number;
  command: string;
  port: number;
  project: string | null;
  type: string;
}

export interface Script {
  pid: number;
  command: string;
  cpu_percent: number;
  mem_percent: number;
  project: string | null;
}

export interface Droplet {
  droplet_id: number;
  name: string;
  status: string;
  ip_address: string | null;
  size_slug: string;
  region: string;
  monthly_cost: number;
}

export interface Ticket {
  id: number;
  project_id: number;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  labels: string[];
  assignee: string;
  due_date: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  project_name?: string;
  project_color?: string;
}

export interface StatusUpdate {
  id: number;
  project_id: number | null;
  ticket_id: number | null;
  content: string;
  author: string;
  update_type: string;
  created_at: string;
  project_name?: string;
  project_color?: string;
}

// Full dashboard types
export interface GitInfo {
  branch: string;
  commit_hash: string;
  commit_message: string;
  commit_ts: number | null;
  uncommitted: number;
  github_url: string | null;
}

export interface TicketCounts {
  [status: string]: number;
}

export interface ClaudeProcess {
  pid: number;
  cpu_percent: number;
  command: string;
  project: string | null;
}

export interface HealthInfo {
  score: number;
  label: 'hot' | 'active' | 'stale' | 'dead' | 'unknown';
}

export interface SessionSummary {
  total: number;
  last_7d: number;
  last_1d: number;
  last_at: string | null;
  total_tokens: number;
}

export interface DashboardProjectFull {
  project: Project;
  git: GitInfo;
  loc: LocSnapshot[];
  tickets: TicketCounts;
  servers: Server[];
  scripts: Script[];
  claude: ClaudeProcess[];
  droplets: Droplet[];
  health: HealthInfo;
  sessions: SessionSummary;
}

export interface SystemSummary {
  server_count: number;
  script_count: number;
  claude_count: number;
  droplet_count: number;
  unlinked_servers: Server[];
  unlinked_scripts: Script[];
}

export interface TimeSummary {
  total_active_s: number;
  project_time: Record<string, number>;
}

export interface FullDashboardResponse {
  projects: DashboardProjectFull[];
  system: SystemSummary;
  feed: StatusUpdate[];
  time: TimeSummary;
  refreshed_at: string;
}

// Dashboard
export const getDashboard = () => request<{ projects: DashboardProject[] }>('/dashboard');
export const getFullDashboard = () => request<FullDashboardResponse>('/dashboard/full');
export const takeSnapshot = () => request<{ snapshots: unknown[] }>('/dashboard/snapshot', { method: 'POST' });

// System
export const getSystemOverview = () =>
  request<{ servers: Server[]; scripts: Script[]; claude_processes: unknown[]; droplets: Droplet[] }>('/system/overview');

// Projects
export const getProjects = () => request<{ projects: Project[] }>('/projects');
export const discoverProjects = () => request<{ discovered: Project[] }>('/projects/discover', { method: 'POST' });

// Tickets
export const getTickets = (params?: Record<string, string>) => {
  const qs = params ? '?' + new URLSearchParams(params).toString() : '';
  return request<{ tickets: Ticket[]; total: number }>(`/tickets${qs}`);
};
export const createTicket = (data: Partial<Ticket>) =>
  request<Ticket>('/tickets', { method: 'POST', body: JSON.stringify(data) });
export const updateTicket = (id: number, data: Partial<Ticket>) =>
  request<Ticket>(`/tickets/${id}`, { method: 'PUT', body: JSON.stringify(data) });

// Feed
export const getFeed = (limit = 50) => request<{ updates: StatusUpdate[] }>(`/feed?limit=${limit}`);
export const postUpdate = (data: Partial<StatusUpdate>) =>
  request<StatusUpdate>('/feed', { method: 'POST', body: JSON.stringify(data) });

// Insights
export const scanSessions = () => request<Record<string, number>>('/insights/scan-sessions', { method: 'POST' });
export const scoreAll = () => request<{ scored: number }>('/insights/score-all', { method: 'POST' });
