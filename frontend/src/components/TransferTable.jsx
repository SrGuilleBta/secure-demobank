import { formatCents, formatDate } from '../money.js'

// Nombres y conceptos se pintan como texto con {} de React, que escapa todo (T-10).
// Prohibido dangerouslySetInnerHTML.
export default function TransferTable({ transfers, me }) {
  if (transfers.length === 0) return <p className="muted">Todavía no hay movimientos.</p>

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Movimiento</th>
            <th>Concepto</th>
            <th className="num">Monto</th>
          </tr>
        </thead>
        <tbody>
          {transfers.map((t) => {
            const sent = t.from_username === me
            return (
              <tr key={t.id}>
                <td>{formatDate(t.created_at)}</td>
                <td>{sent ? `Enviado a ${t.to_username}` : `Recibido de ${t.from_username}`}</td>
                <td className="concept">{t.concept || '—'}</td>
                <td className={`num ${sent ? 'out' : 'in'}`}>
                  {sent ? '−' : '+'}{formatCents(t.amount_cents)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
