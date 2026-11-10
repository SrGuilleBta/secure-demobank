// Validaciones del lado del cliente: solo para avisar antes de enviar. La validación real la hace el backend
// (schemas.py); estas reglas son una copia de las suyas.

export const USERNAME_RULE = 'De 3 a 32 caracteres: minúsculas, números y guion bajo.'
export const PASSWORD_RULE = 'Entre 12 y 128 caracteres, distinta de tu usuario.'

export function normalizeUsername(value) {
  return value.trim().toLowerCase()
}

export function isValidUsername(value) {
  return /^[a-z0-9_]{3,32}$/.test(normalizeUsername(value))
}

export function isValidNewPassword(password, username) {
  return password.length >= 12 && password.length <= 128 && password.toLowerCase() !== normalizeUsername(username)
}

export const CONCEPT_MAX = 100
