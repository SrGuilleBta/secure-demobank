import { api } from '../api.js'
import { usePaged } from '../usePaged.js'
import Pager from '../components/Pager.jsx'
import TransferTable from '../components/TransferTable.jsx'

export default function History({ user }) {
  const { page, setPage, items, loading, error, hasNext } = usePaged(api.transfers)

  return (
    <section className="card">
      <h2>Historial</h2>
      {error && <p className="error" role="alert">{error}</p>}
      {loading ? <p className="muted">Cargando…</p> : !error && <TransferTable transfers={items} me={user.username} />}
      <Pager page={page} hasNext={hasNext} onChange={setPage} />
    </section>
  )
}
