export default function ServiceMap({ edges }) {
  if (!edges.length) {
    return <p className="empty">No service-to-service traffic yet.</p>;
  }

  return (
    <div className="edge-list">
      {edges.map((edge) => (
        <div className="edge-card" key={`${edge.caller}-${edge.callee}`}>
          <div className="edge-flow">
            <span className="badge caller">{edge.caller}</span>
            <span className="arrow">-></span>
            <span className="badge callee">{edge.callee}</span>
          </div>
          <div className="edge-metrics">
            <span>Requests: {edge.request_count}</span>
            <span>Errors: {edge.error_count}</span>
            <span>Avg: {edge.avg_latency_ms.toFixed(2)} ms</span>
          </div>
        </div>
      ))}
    </div>
  );
}
