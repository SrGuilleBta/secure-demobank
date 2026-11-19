import { useState } from 'react'
import { api } from '../api.js'
import { formatDate } from '../money.js'
import { usePaged } from '../usePaged.js'
import Pager from '../components/Pager.jsx'

// Esta pantalla solo se muestra si el rol es "administrador", pero la seguridad la aplica el backend:
// /api/admin/* responde 403 a cualquier otro rol (T-20).
// La bitácora puede traer texto que escribió un usuario (por ejemplo un nombre): se pinta como texto (T-10).

function Users() {
  const { page, setPage, items, loading, error, hasNext } = usePaged(api.adminUsers)
  return (
    <>
      {error && <p className="error" role="alert">{error}</p>}
      {loading ? <p className="muted">Cargando…</p> : !error && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Usuario</th><th>Rol</th><th>Estado</th><th>Alta</th></tr>
            </thead>
            <tbody>
              {items.map((u) => (
                <tr key={u.id}>
                  <td>{u.username}</td>
                  <td>{u.role}</td>
                  <td>{u.locked ? <span className="tag danger">Bloqueado</span> : <span className="tag">Activo</span>}</td>
                  <td>{formatDate(u.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pager page={page} hasNext={hasNext} onChange={setPage} />
    </>
  )
}

function Audit() {
  const { page, setPage, items, loading, error, hasNext } = usePaged(api.adminAudit)
  return (
    <>
      {error && <p className="error" role="alert">{error}</p>}
      {loading ? <p className="muted">Cargando…</p> : !error && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Fecha</th><th>Acción</th><th>Detalle</th><th>Usuario (ID)</th><th>IP</th></tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id}>
                  <td>{formatDate(a.created_at)}</td>
                  <td><code>{a.action}</code></td>
                  <td className="concept">{a.detail ?? '—'}</td>
                  <td className="mono">{a.user_id ? a.user_id.slice(0, 8) : '—'}</td>
                  <td className="mono">{a.ip ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pager page={page} hasNext={hasNext} onChange={setPage} />
    </>
  )
}

export default function Admin() {
  const [tab, setTab] = useState('users')
  return (
    <section className="card">
      <h2>Administración</h2>
      <div className="tabs" role="tablist">
        <button type="button" role="tab" aria-selected={tab === 'users'} onClick={() => setTab('users')}>Usuarios</button>
        <button type="button" role="tab" aria-selected={tab === 'audit'} onClick={() => setTab('audit')}>Bitácora</button>
      </div>
      {tab === 'users' ? <Users /> : <Audit />}
    </section>
  )
}
