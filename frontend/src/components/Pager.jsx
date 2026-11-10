// Paginación simple: la API no devuelve el total, así que "Siguiente" se habilita si la página vino llena.
export default function Pager({ page, hasNext, onChange }) {
  return (
    <div className="pager">
      <button type="button" className="secondary" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        Anterior
      </button>
      <span className="muted">Página {page}</span>
      <button type="button" className="secondary" disabled={!hasNext} onClick={() => onChange(page + 1)}>
        Siguiente
      </button>
    </div>
  )
}
