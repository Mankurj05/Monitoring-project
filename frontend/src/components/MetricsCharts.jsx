import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function MetricsCharts({ latency, errors }) {
  return (
    <div className="charts-grid">
      <div className="panel">
        <h3>Latency by Service (Avg vs P95)</h3>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={latency}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="service_name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="avg_ms" fill="#0f7b6c" name="avg ms" />
            <Bar dataKey="p95_ms" fill="#f66b0e" name="p95 ms" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="panel">
        <h3>Error Volume by Service</h3>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={errors}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="service_name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="total" fill="#4f772d" name="total" />
            <Bar dataKey="errors" fill="#bc4749" name="errors" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
