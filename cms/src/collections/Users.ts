import type { CollectionConfig } from 'payload'
import { adminOnly, adminOnlyField, hasRole, loggedIn, roles } from '@/access/roles'

export const Users: CollectionConfig = {
  slug: 'users',
  labels: { singular: 'Сотрудник', plural: 'Сотрудники' },
  admin: {
    useAsTitle: 'name',
    defaultColumns: ['name', 'email', 'role', 'position'],
    group: 'Редакция',
  },
  auth: true,
  access: {
    read: loggedIn,
    create: adminOnly,
    delete: adminOnly,
    // Admins edit anyone; everyone else edits only their own profile.
    update: ({ req, id }) => hasRole(req.user, 'admin') || req.user?.id === id,
    // Only admins can open the admin panel's user management for others.
    admin: ({ req }) => Boolean(req.user),
  },
  fields: [
    { name: 'name', label: 'Имя и фамилия', type: 'text', required: true },
    { name: 'position', label: 'Должность', type: 'text' },
    {
      name: 'role',
      label: 'Роль',
      type: 'select',
      required: true,
      defaultValue: 'journalist',
      options: [...roles],
      saveToJWT: true,
      access: { create: adminOnlyField, update: adminOnlyField },
      admin: {
        description:
          'Администратор управляет сотрудниками; редактор ставит задачи и публикует; журналист пишет материалы; SMM готовит и отправляет посты.',
      },
    },
  ],
}
