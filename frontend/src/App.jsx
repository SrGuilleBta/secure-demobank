import { useEffect, useState } from 'react'
import { api, hasCsrfToken, setCsrfToken, setUnauthorizedHandler } from './api.js'
import Login from './screens/Login.jsx'
import Register from './screens/Register.jsx'
import Dashboard from './screens/Dashboard.jsx'
import Transfer from './screens/Transfer.jsx'
import History from './screens/History.jsx'
import Admin from './screens/Admin.jsx'

// Navegación con estado (sin librería de rutas, para no sumar dependencias).
// El usuario y el rol viven en memoria; el rol solo decide qué se muestra, la autorización la hace el backend.
export default function App() {
  const [user, setUser] = useState(null) // { username, role }
  const [view, setView] = useState('login')
  const [notice, setNotice] = useState('')
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setCsrfToken(null)
      setUser(null)
      setView('login')
      setNotice('Tu sesión expiró. Inicia sesión de nuevo.')
    })

    // Al recargar, la cookie puede seguir viva pero el token CSRF (que solo está en memoria) se perdió.
    // Sin él no se puede transferir, así que se pide iniciar sesión otra vez.
    api.me()
      .then(() => {
        if (!hasCsrfToken()) setNotice('Por seguridad, al recargar la página debes iniciar sesión de nuevo.')
      })
      .catch(() => {})
      .finally(() => setChecking(false))
  }, [])

  function handleLoggedIn(loggedUser) {
    setUser(loggedUser)
    setNotice('')
    setView('home')
  }

  async function handleLogout() {
    try {
      await api.logout()
    } catch {
      // Aunque falle (por ejemplo la sesión ya había expirado), se limpia el estado local.
    }
    setCsrfToken(null)
    setUser(null)
    setNotice('Cerraste sesión.')
    setView('login')
  }

  if (checking) return <main className="app"><p className="muted">Cargando…</p></main>

  if (!user) {
    return (
      <main className="app">
        <header className="brand">
          <h1>Secure DemoBank</h1>
          <p className="muted">Tu billetera digital</p>
        </header>
        {view === 'register' ? (
          <Register
            onGoLogin={() => setView('login')}
            onRegistered={() => {
              setNotice('Cuenta creada. Ya puedes iniciar sesión.')
              setView('login')
            }}
          />
        ) : (
          <Login notice={notice} onLoggedIn={handleLoggedIn} onGoRegister={() => { setNotice(''); setView('register') }} />
        )}
      </main>
    )
  }

  const isAdmin = user.role === 'administrador'
  const nav = [
    ['home', 'Inicio'],
    ['transfer', 'Transferir'],
    ['history', 'Historial'],
    ...(isAdmin ? [['admin', 'Administración']] : []),
  ]

  return (
    <main className="app">
      <header className="topbar">
        <h1>Secure DemoBank</h1>
        <nav>
          {nav.map(([key, label]) => (
            <button key={key} type="button" className={view === key ? 'nav active' : 'nav'} onClick={() => setView(key)}>
              {label}
            </button>
          ))}
        </nav>
        <div className="who">
          <span className="muted">{user.username}{isAdmin && ' · admin'}</span>
          <button type="button" className="secondary" onClick={handleLogout}>Salir</button>
        </div>
      </header>

      {view === 'home' && <Dashboard user={user} onGoTransfer={() => setView('transfer')} onGoHistory={() => setView('history')} />}
      {view === 'transfer' && <Transfer user={user} onDone={() => setView('home')} />}
      {view === 'history' && <History user={user} />}
      {view === 'admin' && isAdmin && <Admin />}
    </main>
  )
}
