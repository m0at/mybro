import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
} from 'chart.js';
import type { DashboardProject, Server, Droplet } from '../api/client';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler);

interface Props {
  data: DashboardProject;
  servers: Server[];
  droplets: Droplet[];
}

export default function ProjectCard({ data, servers, droplets }: Props) {
  const { project, loc } = data;

  const projectServers = servers.filter((s) => s.project === project.name);
  const projectDroplets = droplets.filter((d) =>
    d.name.toLowerCase().includes(project.slug)
  );

  const labels = loc.map((l) => {
    const d = new Date(l.date);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  });

  const addedData = loc.map((l) => l.lines_added);
  const removedData = loc.map((l) => l.lines_removed);
  const totalNet = addedData.reduce((a, b) => a + b, 0) - removedData.reduce((a, b) => a + b, 0);

  const chartData = {
    labels: labels.length ? labels : ['', '', ''],
    datasets: [
      {
        data: addedData.length ? addedData : [0, 0, 0],
        borderColor: '#4ade80',
        backgroundColor: 'rgba(74, 222, 128, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointBackgroundColor: '#4ade80',
      },
      {
        data: removedData.length ? removedData : [0, 0, 0],
        borderColor: '#f87171',
        backgroundColor: 'rgba(248, 113, 113, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointBackgroundColor: '#f87171',
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { display: false },
      y: { display: false, beginAtZero: true },
    },
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: project.color }}
          />
          <span className="font-semibold text-sm">{project.name}</span>
        </div>
        <div className="flex items-center gap-1.5">
          {projectServers.map((s) => (
            <span
              key={s.port}
              className="badge text-[0.6rem]"
              style={{
                background: 'rgba(74, 222, 128, 0.15)',
                color: '#4ade80',
              }}
              title={`${s.command} :${s.port}`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 mr-1 pulse-dot" />
              :{s.port}
            </span>
          ))}
          {projectDroplets.map((d) => (
            <span
              key={d.droplet_id}
              className="badge text-[0.6rem]"
              style={{
                background:
                  d.status === 'active'
                    ? 'rgba(74, 222, 128, 0.15)'
                    : 'rgba(248, 113, 113, 0.15)',
                color: d.status === 'active' ? '#4ade80' : '#f87171',
              }}
              title={`${d.name} (${d.region})`}
            >
              DO
            </span>
          ))}
        </div>
      </div>

      {/* LOC Sparkline */}
      <div className="h-12 mb-2">
        <Line data={chartData} options={chartOptions} />
      </div>

      {/* Stats row */}
      <div className="flex items-center justify-between text-[0.65rem] text-white/40">
        <span>
          {totalNet >= 0 ? '+' : ''}
          {totalNet} net lines (3d)
        </span>
        <span>
          {loc.reduce((a, l) => a + l.commit_count, 0)} commits
        </span>
      </div>
    </div>
  );
}
