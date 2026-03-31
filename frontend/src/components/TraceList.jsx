export default function TraceList({ traces, selectedTraceId, onSelect }) {
  if (!traces.length) {
    return <p className="empty">No traces collected yet.</p>;
  }

  return (
    <div className="trace-list">
      {traces.map((trace) => (
        <button
          key={trace.trace_id}
          type="button"
          className={`trace-item ${selectedTraceId === trace.trace_id ? "active" : ""}`}
          onClick={() => onSelect(trace.trace_id)}
        >
          <div className="trace-head">
            <span className="trace-id">{trace.trace_id.slice(0, 16)}...</span>
            <span className={`trace-status ${trace.has_error ? "error" : "ok"}`}>
              {trace.has_error ? "Error" : "OK"}
            </span>
          </div>
          <div className="trace-meta">
            <span>Spans: {trace.span_count}</span>
            <span>Total: {trace.total_duration_ms.toFixed(2)} ms</span>
          </div>
        </button>
      ))}
    </div>
  );
}
