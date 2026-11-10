import { useRef, useState } from 'react'
import { api } from '../api.js'
import { MAX_AMOUNT_TEXT, formatCents, parseAmountToCents } from '../money.js'
import { CONCEPT_MAX, isValidUsername, normalizeUsername } from '../validation.js'

export default function Transfer({ user, onDone }) {
  const [to, setTo] = useState('')
  const [amount, setAmount] = useState('')
  const [concept, setConcept] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [sending, setSending] = useState(false)

  // Llave de idempotencia: una nueva por cada transferencia distinta. Si la petición falla por red y se
  // reintenta sin cambiar los datos, se reutiliza la misma para no cobrar dos veces (T-08).
  const idempotencyKey = useRef(crypto.randomUUID())

  function edit(setter) {
    return (event) => {
      setter(event.target.value)
      idempotencyKey.current = crypto.randomUUID() // datos distintos = transferencia distinta
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    const toUsername = normalizeUsername(to)
    const cents = parseAmountToCents(amount)
    if (!isValidUsername(toUsername)) return setError('Escribe un usuario destinatario válido.')
    if (toUsername === user.username) return setError('No puedes transferirte a ti mismo.')
    if (cents === null) return setError(`Escribe un monto mayor a 0 y hasta ${MAX_AMOUNT_TEXT}, con máximo 2 decimales.`)

    setSending(true)
    try {
      const transfer = await api.transfer({
        to_username: toUsername,
        amount_cents: cents,
        concept: concept.trim(),
        idempotency_key: idempotencyKey.current,
      })
      setResult(transfer)
      idempotencyKey.current = crypto.randomUUID()
    } catch (err) {
      if (err.status === 404) setError('No existe un usuario con ese nombre.')
      else if (err.status === 409) setError('Saldo insuficiente.')
      else if (err.status === 422) setError('Revisa el destinatario, el monto y el concepto.')
      else if (err.status === 403) setError('Tu sesión no es válida para transferir. Inicia sesión de nuevo.')
      else setError(err.message)
    } finally {
      setSending(false)
    }
  }

  if (result) {
    return (
      <section className="card">
        <h2>Transferencia enviada</h2>
        <p>
          Enviaste <strong>{formatCents(result.amount_cents)}</strong> a <strong>{result.to_username}</strong>.
        </p>
        {result.concept && <p className="muted concept">Concepto: {result.concept}</p>}
        <div className="actions">
          <button type="button" onClick={onDone}>Volver al inicio</button>
          <button type="button" className="secondary" onClick={() => {
            setResult(null); setTo(''); setAmount(''); setConcept('')
          }}>Otra transferencia</button>
        </div>
      </section>
    )
  }

  return (
    <section className="card">
      <h2>Transferir</h2>
      <form onSubmit={handleSubmit} noValidate>
        <label>
          Usuario destinatario
          <input value={to} onChange={edit(setTo)} maxLength={32} autoComplete="off" required />
        </label>
        <label>
          Monto (MXN)
          <input value={amount} onChange={edit(setAmount)} inputMode="decimal" placeholder="0.00"
            maxLength={10} required />
          <small className="muted">Máximo {MAX_AMOUNT_TEXT} por transferencia.</small>
        </label>
        <label>
          Concepto (opcional)
          <input value={concept} onChange={edit(setConcept)} maxLength={CONCEPT_MAX} />
          <small className="muted">{concept.length}/{CONCEPT_MAX}</small>
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="actions">
          <button type="submit" disabled={sending}>{sending ? 'Enviando…' : 'Enviar'}</button>
          <button type="button" className="secondary" onClick={onDone}>Cancelar</button>
        </div>
      </form>
    </section>
  )
}
