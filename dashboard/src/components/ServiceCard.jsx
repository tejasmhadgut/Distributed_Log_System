import MetricsChart from './MetricsChart'

function Stat({ label, value, color }) {
  return (
    <div>
      <div style={{ color: '#6c7086', fontSize: '11px', marginBottom: '2px' }}>{label}</div>
      <div style={{ color: color || '#cdd6f4', fontWeight: 'bold', fontSize: '16px' }}>{value}</div>
    </div>
  )
}

export default function ServiceCard({ service, history }) {
  const errorRate = service.error_rate
  const statusColor = errorRate > 10 ? '#f38ba8' : errorRate > 5 ? '#f9e2af' : '#a6e3a1'

  return (
    <div style={{
      background: '#1e1e2e',
      border: `1px solid ${statusColor}`,
      borderRadius: '8px',
      padding: '16px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h3 style={{ margin: 0, color: '#cdd6f4', fontSize: '14px' }}>{service.service_name}</h3>
        <span style={{
          background: statusColor,
          color: '#11111b',
          borderRadius: '4px',
          padding: '2px 8px',
          fontSize: '12px',
          fontWeight: 'bold',
        }}>
          {errorRate.toFixed(1)}% err
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
        <Stat label="Requests" value={service.request_count} />
        <Stat label="Errors" value={service.error_count} />
        <Stat label="p95 Latency" value={`${service.latency_p95}ms`} />
        <Stat label="Error Rate" value={`${errorRate.toFixed(1)}%`} color={statusColor} />
      </div>

      <MetricsChart history={history} />
    </div>
  )
}
