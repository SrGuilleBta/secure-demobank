import { useState } from 'react'
import { api, setCsrfToken } from '../api.js'
import { normalizeUsername } from '../validation.js'

export default function Login({ onLoggedIn, onGoRegister, notice }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSending(true)
    try {
      const data = await api.login(normalizeUsername(username), password)
      setCsrfToken(data.csrf_token) // solo en memoria (T-09)
      onLoggedIn({ username: data.username, role: data.role })
    } catch (err) {
      // Mismo mensaje para usuario inexistente, contraseña incorrecta o cuenta bloqueada (no revela cuentas).
      setError(err.status === 401 || err.status === 422 ? 'Usuario o contraseña incorrectos.' : err.message)
      setPassword('')
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="card auth">
      <h2>Iniciar sesión</h2>
      {notice && <p className="notice">{notice}</p>}
      <form onSubmit={handleSubmit} noValidate>
        <label>
          Usuario
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username"
            maxLength={32} required />
        </label>
        <label>
          Contraseña
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password" maxLength={128} required />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" disabled={sending || !username || !password}>
          {sending ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
      <p className="muted">
        ¿No tienes cuenta? <button type="button" className="link" onClick={onGoRegister}>Regístrate</button>
      </p>
    </section>
  )
}
