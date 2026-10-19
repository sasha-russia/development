import type { CollectionConfig } from 'payload'
import { forbidden, hasRole, isEditor, loggedIn, ownOrEditor } from '@/access/roles'
import { requestSiteRebuild } from '@/lib/siteRebuild'
import { slugify } from '@/lib/slug'

export const formats = [
  { label: 'Новость', value: 'news' },
  { label: 'История', value: 'story' },
  { label: 'Карточки', value: 'cards' },
  { label: 'Тест', value: 'test' },
  { label: 'Подкаст', value: 'podcast' },
]

export const Articles: CollectionConfig = {
  slug: 'articles',
  labels: { singular: 'Материал', plural: 'Материалы' },
  admin: {
    useAsTitle: 'title',
    defaultColumns: ['title', 'format', 'author', '_status', 'updatedAt'],
    group: 'Контент',
    description: 'Материалы для сайта. Журналист сохраняет черновик, публикует редактор.',
  },
  versions: {
    drafts: { autosave: { interval: 2000 } },
    maxPerDoc: 50,
  },
  access: {
    // Anyone may read published articles (the site build does); staff also see drafts.
    read: ({ req }) => (req.user ? true : { _status: { equals: 'published' } }),
    create: ({ req }) => hasRole(req.user, 'admin', 'editor', 'journalist'),
    update: ownOrEditor('author'),
    delete: ({ req }) => isEditor(req.user),
    readVersions: loggedIn,
  },
  hooks: {
    beforeValidate: [
      ({ data, req, operation }) => {
        if (!data) return data
        if (operation === 'create' && !data.author && req.user) data.author = req.user.id
        if (!data.slug && data.title) data.slug = slugify(data.title)
        return data
      },
    ],
    beforeChange: [
      ({ data, req, originalDoc }) => {
        const publishing = data._status === 'published'
        const wasPublished = originalDoc?._status === 'published'
        if ((publishing || wasPublished) && req.user && !isEditor(req.user)) {
          forbidden('Публиковать и менять опубликованные материалы может только редактор.')
        }
        if (publishing && !data.publishedAt) data.publishedAt = new Date().toISOString()
        return data
      },
    ],
    afterChange: [
      ({ doc, previousDoc, req }) => {
        if (doc._status === 'published' || previousDoc?._status === 'published') {
          void requestSiteRebuild(req.payload, `article ${doc.slug}`)
        }
        return doc
      },
    ],
    afterDelete: [
      ({ doc, req }) => {
        if (doc._status === 'published') void requestSiteRebuild(req.payload, `deleted ${doc.slug}`)
      },
    ],
  },
  fields: [
    { name: 'title', label: 'Заголовок', type: 'text', required: true },
    {
      name: 'lead',
      label: 'Подзаголовок (лид)',
      type: 'textarea',
      required: true,
      maxLength: 400,
    },
    {
      name: 'format',
      label: 'Формат',
      type: 'select',
      required: true,
      defaultValue: 'news',
      options: formats,
    },
    { name: 'photo', label: 'Главное фото', type: 'upload', relationTo: 'media' },
    {
      name: 'body',
      label: 'Текст',
      type: 'richText',
      admin: { condition: (data) => data.format !== 'cards' && data.format !== 'test' },
    },
    {
      name: 'cards',
      label: 'Карточки',
      type: 'array',
      labels: { singular: 'Карточка', plural: 'Карточки' },
      admin: { condition: (data) => data.format === 'cards' },
      fields: [
        { name: 'title', label: 'Вопрос', type: 'text', required: true },
        { name: 'text', label: 'Ответ', type: 'textarea', required: true },
      ],
    },
    {
      name: 'questions',
      label: 'Вопросы теста',
      type: 'array',
      labels: { singular: 'Вопрос', plural: 'Вопросы' },
      admin: { condition: (data) => data.format === 'test' },
      fields: [
        { name: 'text', label: 'Вопрос', type: 'text', required: true },
        {
          name: 'options',
          label: 'Варианты ответа',
          type: 'array',
          minRows: 2,
          fields: [{ name: 'text', label: 'Вариант', type: 'text', required: true }],
        },
        {
          name: 'answer',
          label: 'Номер правильного варианта',
          type: 'number',
          required: true,
          min: 1,
        },
        { name: 'explanation', label: 'Пояснение', type: 'textarea' },
      ],
    },
    {
      name: 'duration',
      label: 'Длительность',
      type: 'text',
      admin: { condition: (data) => data.format === 'podcast', placeholder: '32 минуты' },
    },
    {
      name: 'featured',
      label: 'Главная новость',
      type: 'checkbox',
      defaultValue: false,
      admin: {
        position: 'sidebar',
        description: 'Крупно на первом экране главной. Нужна фотография; берётся самая свежая из отмеченных.',
      },
    },
    {
      name: 'slug',
      label: 'Адрес (slug)',
      type: 'text',
      unique: true,
      index: true,
      admin: { position: 'sidebar', description: 'Заполняется из заголовка, можно изменить.' },
    },
    {
      name: 'author',
      label: 'Автор',
      type: 'relationship',
      relationTo: 'users',
      access: { update: ({ req }) => isEditor(req.user) },
      admin: { position: 'sidebar' },
    },
    {
      name: 'publishedAt',
      label: 'Дата публикации',
      type: 'date',
      admin: {
        position: 'sidebar',
        date: { pickerAppearance: 'dayAndTime' },
        description: 'Ставится при первой публикации.',
      },
    },
  ],
}
