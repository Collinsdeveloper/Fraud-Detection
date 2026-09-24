import { getUser, setToken, setUser } from '../api'

const NAV = [
  {
    group: 'Monitor',
    items: [
      { route: '/', label: 'Dashboard', icon: '🛡️', live: true },
      { route: '/sim-swaps', label: 'SIM Swaps', icon: '📱' },
      { route: '/airtime', label: 'Airtime', icon: '💸' },
      { route: '/account', label: 'Account Takeovers', icon: '🔓' },
      { route: '/alerts', label: 'Alerts', icon: '🚨', live: true },
    ],
  },
  {
    group: 'Manage',
    items: [
      { route: '/subscribers', label: 'Subscribers', icon: '👥' },
      { route: '/rules', label: 'Detection Rules', icon: '🧭' },
    ],
  },
  {
    group: 'Playground',
    items: [
      { route: '/simulator', label: 'Event Simulator', icon: '🧪' },
      { route: '/notifications', label: 'Notification Logs', icon: '📨' },
    ],
  },
]

export function Layout({ route, children }) {
  const user = getUser() || {}
  const initials = (user.full_name || user.email || 'U')
    .split(' ')
    .map((p) => p[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  const logout = () => {
    setToken(null)
    setUser(null)
    window.location.hash = '#/login'
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">🛡️</div>
          <div>
            <div className="name">FraudShield</div>
            <div className="tag">Telco Security Suite</div>
          </div>
        </div>
        <nav className="nav">
          {NAV.map((g) => (
            <div key={g.group}>
              <div className="sec">{g.group}</div>
              {g.items.map((it) => (
                <a
                  key={it.route}
                  href={`#${it.route}`}
                  className={route === it.route ? 'active' : ''}
                >
                  <span className="ic">{it.icon}</span>
                  <span>{it.label}</span>
                  {it.live && <span className="dot" />}
                </a>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          Engine v1.0 · AT Sandbox<br />Africa's Talking SMS + Voice
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div>
            <h1>{titleFor(route)}</h1>
            <div className="sub">{subFor(route)}</div>
          </div>
          <div className="spacer" />
          <span className="live-pill">
            <span className="pulse" /> LIVE
          </span>
          <div className="user-chip">
            <div className="avatar">{initials}</div>
            <div className="who">
              <b>{user.full_name || user.email}</b>
              <span>{user.role || 'operator'}</span>
            </div>
            <button className="btn-logout" onClick={logout}>Sign out</button>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  )
}

function titleFor(route) {
  const map = {
    '/': ['Command Center', 'Real-time fraud posture'],
    '/sim-swaps': ['SIM Swap Monitor', 'Suspicious SIM re-issuance events'],
    '/airtime': ['Airtime Monitor', 'Unusual airtime transfer patterns'],
    '/account': ['Account Takeover Monitor', 'Suspicious login & profile events'],
    '/notifications': ['Notification Logs', 'Africa\'s Talking delivery audit trail'],

    '/alerts': ['Alert Console', 'Open fraud alerts and subscriber notifications'],
    '/subscribers': ['Subscribers', 'Lines under surveillance'],
    '/rules': ['Detection Rules', 'Configurable risk-engine weights'],
    '/simulator': ['Event Simulator', 'Generate realistic fraud events'],
  }
  return map[route] || ['FraudShield', '']
}
function subFor(route) {
  return titleFor(route)[1]
}
