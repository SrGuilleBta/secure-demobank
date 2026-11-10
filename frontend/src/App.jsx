import { useEffect, useState } from 'react'

// Pantalla inicial: comprueba que el frontend llega a la API a través del proxy.
// Reemplazar por las pantallas reales (registro, login, saldo, transferencias, historial, administrador).
export default function App() {
  const [apiStatus, setApiStatus] = useState('comprobando...')

  useEffect(() => {
    fetch('/api/health')
      .then((response) => response.json())
      .then((data) => setApiStatus(data.status))
      .catch(() => setApiStatus('sin conexión'))
  }, [])

  return (
    <main className="app">
      <h1>Secure DemoBank</h1>
      <p>Estado de la API: {apiStatus}</p>
    </main>
  )
}
