import { useEffect, useMemo, useState } from "react";

import { api } from "./api";
import MetricsCharts from "./components/MetricsCharts";
import ServiceMap from "./components/ServiceMap";
import TraceList from "./components/TraceList";

export default function App() {
  const [traces, setTraces] = useState([]);
  const [selectedTraceId, setSelectedTraceId] = useState("");
  const [selectedTraceSpans, setSelectedTraceSpans] = useState([]);
  const [edges, setEdges] = useState([]);
  const [services, setServices] = useState([]);
  const [latency, setLatency] = useState([]);
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [tracesResult, edgeResult, servicesResult, latencyResult, errorResult] = await Promise.allSettled([
        api.getTraces(30),
        api.getServiceMap(120),
        api.getServices(),
        api.getLatency(120),
        api.getErrors(120),
      ]);

      const tracesData = tracesResult.status === "fulfilled" ? tracesResult.value : [];
      const edgeData = edgeResult.status === "fulfilled" ? edgeResult.value : [];
      const servicesData = servicesResult.status === "fulfilled" ? servicesResult.value : [];
      const latencyData = latencyResult.status === "fulfilled" ? latencyResult.value : [];
      const errorData = errorResult.status === "fulfilled" ? errorResult.value : [];

      setTraces(tracesData);
      setEdges(edgeData);
      setServices(servicesData);
      setLatency(latencyData);
      setErrors(errorData);

      if (tracesData.length && !selectedTraceId) {
        setSelectedTraceId(tracesData[0].trace_id);
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
    const timer = setInterval(loadDashboard, 5000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!selectedTraceId) {
      setSelectedTraceSpans([]);
      return;
    }

    api.getTrace(selectedTraceId).then(setSelectedTraceSpans).catch(console.error);
  }, [selectedTraceId]);

  const traceDuration = useMemo(
    () => selectedTraceSpans.reduce((acc, span) => acc + span.duration_ms, 0),
    [selectedTraceSpans]
  );

  return (
    <main className="dashboard">
      <header className="hero panel">
        <h1>PulseMesh Monitor</h1>
        <p>Distributed tracing and service debugging dashboard for your FastAPI microservices.</p>
        <button type="button" onClick={loadDashboard} disabled={loading} className="refresh-btn">
          {loading ? "Refreshing..." : "Refresh Now"}
        </button>
      </header>

      <section className="panel">
        <h2>Service Dependency Graph</h2>
        <ServiceMap edges={edges} />
      </section>

      <section className="panel">
        <h2>Service Metadata</h2>
        {!services.length && <p className="empty">No service metadata yet.</p>}
        {!!services.length && (
          <div className="service-meta-grid">
            {services.map((svc) => (
              <div className="service-meta-card" key={`${svc.tenant_id}-${svc.project_id}-${svc.service_name}`}>
                <div className="service-meta-head">
                  <strong>{svc.service_name}</strong>
                  <span>{svc.environment || "n/a"}</span>
                </div>
                <div className="service-meta-row">Version: {svc.service_version || "n/a"}</div>
                <div className="service-meta-row">Team: {svc.team || "n/a"}</div>
                <div className="service-meta-row">Tenant: {svc.tenant_id}</div>
                <div className="service-meta-row">Project: {svc.project_id}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      <MetricsCharts latency={latency} errors={errors} />

      <section className="panel trace-section">
        <div>
          <h2>Recent Traces</h2>
          <TraceList traces={traces} selectedTraceId={selectedTraceId} onSelect={setSelectedTraceId} />
        </div>

        <div>
          <h2>Trace Timeline</h2>
          <p className="trace-summary">Total selected trace duration: {traceDuration.toFixed(2)} ms</p>
          <div className="span-list">
            {selectedTraceSpans.map((span) => (
              <div className={`span-row ${span.is_error ? "error" : ""}`} key={span.span_id}>
                <strong>{span.service_name}</strong>
                <span>{span.method} {span.path}</span>
                <span>{span.duration_ms.toFixed(2)} ms</span>
                <span>Status {span.status_code}</span>
              </div>
            ))}
            {!selectedTraceSpans.length && <p className="empty">Select a trace to view spans.</p>}
          </div>
        </div>
      </section>
    </main>
  );
}
