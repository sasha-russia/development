import { APIError, type Access, type FieldAccess, type Where } from 'payload'

export const roles = [
  { label: 'Администратор', value: 'admin' },
  { label: 'Редактор', value: 'editor' },
  { label: 'Журналист', value: 'journalist' },
  { label: 'SMM', value: 'smm' },
] as const

export type Role = (typeof roles)[number]['value']

type UserLike = { id: number | string; role?: Role | null } | null | undefined

export function hasRole(user: UserLike, ...allowed: Role[]): boolean {
  return Boolean(user?.role && allowed.includes(user.role))
}

export const isEditor = (user: UserLike) => hasRole(user, 'admin', 'editor')

export const loggedIn: Access = ({ req }) => Boolean(req.user)

export const adminOnly: Access = ({ req }) => hasRole(req.user, 'admin')

export const editorsOnly: Access = ({ req }) => isEditor(req.user)

export const adminOnlyField: FieldAccess = ({ req }) => hasRole(req.user, 'admin')

// Editors see everything; everyone else sees documents they own or are assigned to.
export function ownOrEditor(...ownerFields: string[]): Access {
  return ({ req }) => {
    if (!req.user) return false
    if (isEditor(req.user)) return true
    return { or: ownerFields.map((field) => ({ [field]: { equals: req.user!.id } })) } as Where
  }
}

export function forbidden(message: string): never {
  throw new APIError(message, 403, null, true)
}
