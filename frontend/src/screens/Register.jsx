import { useState } from 'react'
import { api } from '../api.js'
import { PASSWORD_RULE, USERNAME_RULE, isValidNewPassword, isValidUsername, normalizeUsername } from '../validation.js'

export default function Register({ onRegistered, onGoLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)

  function validate() {
    if (!isValidUsername(username)) return `Usuario no válido. ${USERNAME_RULE}`
    if (!isValidNewPassword(password, username)) return `Contraseña no válida. ${PASSWORD_RULE}`
    if (password !== confirm) return 'Las contraseñas no coinciden.'
    return ''
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const problem = validate()
    setError(problem)
    if (problem) return

    setSending(true)
    try {
      await api.register(normalizeUsername(username), password)
      onRegistered(normalizeUsername(username))
    } catch (err) {
      if (err.status === 409) setError('Ese usuario no está disponible. Elige otro.')
      else if (err.status === 422 && err.fields.username) setError(`Usuario no válido. ${USERNAME_RULE}`)
      else if (err.status === 422) setError(`Contraseña no válida. ${PASSWORD_RULE}`)
      else setError(err.message)
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="card auth">
      <h2>Crear cuenta</h2>
      <form onSubmit={handleSubmit} noValidate>
        <label>
          Usuario
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username"
            maxLength={32} required />
          <small className="muted">{USERNAME_RULE}</small>
        </label>
        <label>
          Contraseña
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password" maxLength={128} required />
          <small className="muted">{PASSWORD_RULE}</small>
        </label>
        <label>
          Confirmar contraseña
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password" maxLength={128} required />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" disabled={sending}>{sending ? 'Creando…' : 'Crear cuenta'}</button>
      </form>
      <p className="muted">
        ¿Ya tienes cuenta? <button type="button" className="link" onClick={onGoLogin}>Inicia sesión</button>
      </p>
    </section>
  )
}
