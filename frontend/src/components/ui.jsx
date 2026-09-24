export function Modal({ title, onClose, children, width }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal"
        style={width ? { width } : undefined}
        onClick={(e) => e.stopPropagation()}
      >
        <h3>{title}</h3>
        {children}
      </div>
    </div>
  )
}

export function Donut({ data, colors, size = 130 }) {
  const entries = Object.entries(data || {}).filter(([, v]) => v > 0)
  const total = entries.reduce((s, [, v]) => s + v, 0)
  if (total === 0) {
    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2} cy={size / 2} r={size / 2 - 8}
          fill="none" stroke="#1e2945" strokeWidth="12"
        />
      </svg>
    )
  }
  const r = size / 2 - 8
  const circ = 2 * Math.PI * r
  let offset = 0
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1e2945" strokeWidth="12" />
      {entries.map(([k, v]) => {
        const frac = v / total
        const dash = frac * circ
        const el = (
          <circle
            key={k}
            cx={size / 2} cy={size / 2} r={r}
            fill="none" stroke={colors[k] || '#64748b'} strokeWidth="12"
            strokeDasharray={`${dash} ${circ - dash}`} strokeDashoffset={-offset}
            strokeLinecap="butt"
          />
        )
        offset += dash
        return el
      })}
    </svg>
  )
}

export function StackedBars({ series, days, colors }) {
  // series: [{ name, values: [n per day] }] aligned with `days`
  const perDayTotals = days.map((d, i) =>
    series.reduce((s, srs) => s + Number(srs.values[i] ?? 0), 0),
  )
  const max = Math.max(1, ...perDayTotals)
  return (
    <div className="bars">
      {days.map((d, i) => {
        const total = perDayTotals[i]
        const date = new Date(`${d.date}T00:00:00`)
        const lbl = date.toLocaleDateString('en-KE', { day: '2-digit', month: 'short' })
        return (
          <div className="bar-col" key={d.date}>
            <div className="stack">
              {series.map((srs, j) => {
                const v = srs.values[i] ?? 0
                const h = `${(v / max) * 100}%`
                return (
                  <div
                    key={j}
                    className="seg"
                    style={{ height: h, background: colors[j % colors.length], opacity: 0.85 }}
                    title={`${srs.name}: ${v}`}
                  />
                )
              })}
            </div>
            <div className="total">{total || ''}</div>
            <div className="lbl">{lbl}</div>
          </div>
        )
      })}
    </div>
  )
}

export function Sparkline({ values, color = '#22d3ee', height = 36 }) {
  const w = 120
  const max = Math.max(1, ...values)
  const pts = values
    .map((v, i) => `${(i / (values.length - 1 || 1)) * w},${height - (v / max) * (height - 4) - 2}`)
    .join(' ')
  return (
    <svg width="100%" height={height} viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none">
      <polyline points={`0,${height - 2} ${pts} ${w},${height - 2}`} fill="none" stroke={color} strokeWidth="2" />
    </svg>
  )
}

export function Pager({ pagination, onPage }) {
  if (!pagination) return null
  const { page, pages, total, has_next, has_prev } = pagination
  return (
    <div className="pager">
      <button disabled={!has_prev} onClick={() => onPage(page - 1)}>‹ Prev</button>
      <span>
        Page {page} of {Math.max(pages, 1)} · {total} records
      </span>
      <button disabled={!has_next} onClick={() => onPage(page + 1)}>Next ›</button>
    </div>
  )
}
