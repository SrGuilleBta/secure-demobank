// Cliente de la API. Todo va al mismo origen (/api/...), sin CORS: lo resuelve el proxy.
//
// Token CSRF (T-09): se guarda SOLO en memoria (esta variable del módulo), nunca en localStorage ni sessionStorage.
// Si se recarga la página se pierde y hay que iniciar sesión otra vez: es a propósito.
let csrfToken = null

// Lo registra App para mandar al login cuando la sesión expira (401).
let onUnauthorized = () => {}

export function setCsrfToken(token) {
  csrfToken = token
}

export function hasCsrfToken() {
  return csrfToken !== null
}

export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler
}

// Error con mensaje propio para el usuario. Nunca se muestra el texto crudo de la API (T-14).
export class ApiError extends Error {
  constructor(status, message, fields = {}) {
    super(message)
    this.status = status
    this.fields = fields // { campo: mensaje propio } para errores 422
  }
}

const GENERIC_MESSAGES = {
  401: 'Tu sesión expiró. Inicia sesión de nuevo.',
  403: 'No tienes permiso para hacer esto.',
  404: 'No se encontró lo que buscas.',
  409: 'La operación no se pudo completar.',
  422: 'Revisa los datos del formulario.',
  429: 'Demasiados intentos. Espera un momento y vuelve a intentar.',
}

async function request(method, path, body) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  // Toda petición que cambia datos lleva el token anti-CSRF (T-09).
  if (method !== 'GET' && csrfToken) headers['X-CSRF-Token'] = csrfToken

  let response
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'same-origin',
    })
  } catch {
    throw new ApiError(0, 'No hay conexión con el servidor. Intenta de nuevo.')
  }

  if (response.status === 204) return null

  let data = null
  try {
    data = await response.json()
  } catch {
    // Respuesta sin JSON (por ejemplo un 502 del proxy): se trata como error genérico.
  }

  if (response.ok) return data

  // Los campos que fallaron en un 422 se conservan para que cada pantalla ponga su propio mensaje.
  const fields = {}
  if (response.status === 422 && Array.isArray(data?.detail)) {
    for (const error of data.detail) fields[error.campo ?? ''] = true
  }

  if (response.status === 401 && path !== '/api/auth/login') onUnauthorized()

  const message = GENERIC_MESSAGES[response.status] ?? 'Ocurrió un error. Intenta más tarde.'
  const error = new ApiError(response.status, message, fields)
  // El detalle de texto solo se usa para distinguir casos conocidos; no se muestra tal cual.
  error.detailCode = typeof data?.detail === 'string' ? data.detail : null
  throw error
}

export const api = {
  register: (username, password) => request('POST', '/api/auth/register', { username, password }),
  login: (username, password) => request('POST', '/api/auth/login', { username, password }),
  logout: () => request('POST', '/api/auth/logout'),
  me: () => request('GET', '/api/me'),
  account: () => request('GET', '/api/account'),
  transfer: (payload) => request('POST', '/api/transfers', payload),
  transfers: (page, pageSize) => request('GET', `/api/transfers?page=${page}&page_size=${pageSize}`),
  adminUsers: (page, pageSize) => request('GET', `/api/admin/users?page=${page}&page_size=${pageSize}`),
  adminAudit: (page, pageSize) => request('GET', `/api/admin/audit?page=${page}&page_size=${pageSize}`),
}
