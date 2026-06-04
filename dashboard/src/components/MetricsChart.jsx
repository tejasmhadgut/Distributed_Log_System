import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'

export default function MetricsChart({ history }) {
  if (!history || history.length < 2) {
    return (
      <div style={{ color: '#6c7086', fontSize: '12px', textAlign: 'center', padding: '8px 0' }}>
        Waiting for data...
      </div>
    )
  }

  const data = history.map((h, i) => ({
    t: i,
    error_rate: h.error_rate,
    latency: h.latency_p95,
  }))

  return (
    <ResponsiveContainer width="100%" height={80}>
      <LineChart data={data}>
      
        <XAxis dataKey="t" hide />
        <YAxis hide domain={[0, 'auto']} />
        <Tooltip
          contentStyle={{ background: '#313244', border: 'none', fontSize: '12px', color: '#cdd6f4' }}
          formatter={(v, name) => [
            name === 'error_rate' ? `${v}%` : `${v}ms`,
            name === 'error_rate' ? 'Error Rate' : 'p95 Latency',
          ]}
          labelFormatter={() => ''}
        />
        <Legend
          formatter={(value) => value === 'error_rate' ? 'Error Rate' : 'p95 Latency'}
          wrapperStyle={{ fontSize: '11px', color: '#6c7086' }}
        />
        <Line type="monotone" dataKey="error_rate" stroke="#f38ba8" dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="latency" stroke="#89b4fa" dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  )
}
