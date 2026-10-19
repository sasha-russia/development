import type { CollectionConfig } from 'payload'
import { editorsOnly, loggedIn } from '@/access/roles'

export const Media: CollectionConfig = {
  slug: 'media',
  labels: { singular: 'Изображение', plural: 'Медиатека' },
  admin: { group: 'Контент' },
  access: {
    // The public site build reads images directly.
    read: () => true,
    create: loggedIn,
    update: loggedIn,
    delete: editorsOnly,
  },
  fields: [
    { name: 'alt', label: 'Описание для незрячих', type: 'text', required: true },
    { name: 'credit', label: 'Автор и лицензия', type: 'text' },
    { name: 'sourceUrl', label: 'Источник', type: 'text' },
  ],
  upload: {
    mimeTypes: ['image/*'],
  },
}
