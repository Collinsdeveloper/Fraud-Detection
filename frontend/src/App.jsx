import { useEffect, useState } from 'react'
import { getToken, isAuthed } from './api'
import { Layout } from './components/Layout'
import { ToastHost } from './components/toast.jsx'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { MonitorPage } from './pages/MonitorPage'
import { AlertsPage } from './pages/AlertsPage'
import { SubscribersPage } from './pages/SubscribersPage'
import { RulesPage } from './pages/RulesPage'
import { SimulatorPage } from './pages/SimulatorPage'
import { NotificationsPage } from './pages/NotificationsPage'

const routeFromHash = () => {
  const route = window.location.hash.replace(/^#/, '') || '/'
  return route.startsWith('/') ? route : `/${route}`
}

function pageFor(route) {
  switch (route) {
    case '/': return <Dashboard />
    case '/sim-swaps': return <MonitorPage kind="sim-swap" />
    case '/airtime': return <MonitorPage kind="airtime" />
    case '/account': return <MonitorPage kind="account" />
    case '/alerts': return <AlertsPage />
    case '/subscribers': return <SubscribersPage />
    case '/rules': return <RulesPage />
    case '/simulator': return <SimulatorPage />
    case '/notifications': return <NotificationsPage />
    default: return <Dashboard />
  }
}

function App() {
  const [route, setRoute] = useState(routeFromHash)
  const [authed, setAuthed] = useState(isAuthed())

  useEffect(() => {
    const onHashChange = () => {
      setRoute(routeFromHash())
      setAuthed(!!getToken())
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    if (!authed && route !== '/login') window.location.hash = '#/login'
    if (authed && route === '/login') window.location.hash = '#/'
  }, [authed, route])

  if (!authed || route === '/login') return <><Login onLogin={() => setAuthed(true)} /><ToastHost /></>

  return (
    <>
      <Layout route={route}>{pageFor(route)}</Layout>
      <ToastHost />
    </>
  )
}

export default App
