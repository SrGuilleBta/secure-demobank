import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { formatCents } from '../money.js'
import TransferTable from '../components/TransferTable.jsx'

export default function Dashboard({ user, onGoTransfer, onGoHistory }) {
  const [balance, setBalance] = useState(null)
  const [recent, setRecent] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([api.account(), api.transfers(1, 5)])
      .then(([account, transfers]) => {
        if (!active) return
        setBalance(account.balance_cents)
        setRecent(transfers)
      })
      .catch((err) => active && setError(err.message))
    return () => {
      active = false
    }
  }, [])

  return (
    <>
      <section className="card balance">
        <p className="muted">Saldo disponible</p>
        <p className="amount">{balance === null ? '…' : formatCents(balance)}</p>
        <button type="button" onClick={onGoTransfer}>Transferir</button>
      </section>
      <section className="card">
        <div className="card-head">
          <h2>Últimos movimientos</h2>
          <button type="button" className="link" onClick={onGoHistory}>Ver todo</button>
        </div>
        {error ? <p className="error" role="alert">{error}</p> : <TransferTable transfers={recent} me={user.username} />}
      </section>
    </>
  )
}
