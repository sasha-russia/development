import type { CollectionConfig } from 'payload'
import { isEditor, loggedIn, ownOrEditor } from '@/access/roles'

export const Tasks: CollectionConfig = {
  slug: 'tasks',
  labels: { singular: 'Задача', plural: 'Задачи' },
  admin: {
    useAsTitle: 'title',
    defaultColumns: ['title', 'status', 'assignee', 'dueDate', 'priority'],
    group: 'Редакция',
    description: 'Задания редакции: кто, что и к какому сроку делает.',
  },
  access: {
    read: ownOrEditor('assignee', 'createdBy'),
    create: loggedIn,
    update: ownOrEditor('assignee', 'createdBy'),
    delete: ({ req }) => isEditor(req.user),
  },
  hooks: {
    beforeValidate: [
      ({ data, req, operation }) => {
        if (data && operation === 'create' && req.user) data.createdBy = req.user.id
        return data
      },
    ],
  },
  fields: [
    { name: 'title', label: 'Задача', type: 'text', required: true },
    { name: 'description', label: 'Описание', type: 'textarea' },
    {
      type: 'row',
      fields: [
        {
          name: 'status',
          label: 'Статус',
          type: 'select',
          required: true,
          defaultValue: 'new',
          options: [
            { label: 'Новая', value: 'new' },
            { label: 'В работе', value: 'in_progress' },
            { label: 'На проверке', value: 'review' },
            { label: 'Готово', value: 'done' },
          ],
        },
        {
          name: 'priority',
          label: 'Срочность',
          type: 'select',
          defaultValue: 'normal',
          options: [
            { label: 'Обычная', value: 'normal' },
            { label: 'Срочно', value: 'urgent' },
          ],
        },
      ],
    },
    {
      name: 'assignee',
      label: 'Ответственный',
      type: 'relationship',
      relationTo: 'users',
      required: true,
      // Only editors reassign; an assignee can't hand their task to someone else.
      access: { update: ({ req }) => isEditor(req.user) },
    },
    {
      name: 'dueDate',
      label: 'Срок',
      type: 'date',
      admin: { date: { pickerAppearance: 'dayAndTime' } },
    },
    {
      name: 'article',
      label: 'Материал',
      type: 'relationship',
      relationTo: 'articles',
    },
    {
      name: 'socialPost',
      label: 'Пост для соцсетей',
      type: 'relationship',
      relationTo: 'social-posts',
    },
    {
      name: 'createdBy',
      label: 'Поставил',
      type: 'relationship',
      relationTo: 'users',
      access: { update: () => false },
      admin: { position: 'sidebar', readOnly: true },
    },
  ],
}
