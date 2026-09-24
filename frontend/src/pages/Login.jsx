import { useState } from 'react'
import { api, setToken, setUser } from '../api'

export function Login() {
  const [email, setEmail] = useState('admin@fraudshield.io')
  const [password, setPassword] = useState('Admin@123')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const res = await api.post('/auth/login', { email, password })
      setToken(res.token)
      setUser(res.user)
      window.location.hash = '#/'
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <div className="logo">🛡️</div>
        <h1>FraudShield</h1>
        <p className="tagline">
          SIM swap · airtime fraud · account takeover monitoring
        </p>
        <label htmlFor="email">Email</label>
        <input
          id="email" className="input" type="email" autoComplete="username"
          value={email} onChange={(e) => setEmail(e.target.value)} required
        />
        <label htmlFor="password">Password</label>
        <input
          id="password" className="input" type="password" autoComplete="current-password"
          value={password} onChange={(e) => setPassword(e.target.value)} required
        />
        <button className="btn primary" type="submit" disabled={busy}>
          {busy ? 'Signing in…' : 'Enter Command Center'}
        </button>
        {error && <div className="err-msg">{error}</div>}
        <div className="demo-hint">
          Demo credentials:<br />
          <code>admin@fraudshield.io</code> / <code>Admin@123</code>
          <br />or <code>analyst@fraudshield.io</code> / <code>Analyst@123</code>
        </div>
      </form>
    </div>
  )
}
