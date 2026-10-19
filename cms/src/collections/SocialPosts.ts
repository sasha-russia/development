import type { CollectionConfig } from 'payload'
import { hasRole, isEditor, loggedIn } from '@/access/roles'
import { channelOptions, sendSocialPost } from '@/lib/social'

const canPost = (user: Parameters<typeof hasRole>[0]) => hasRole(user, 'admin', 'editor', 'smm')

export const SocialPosts: CollectionConfig = {
  slug: 'social-posts',
  labels: { singular: 'Пост для соцсетей', plural: 'Посты для соцсетей' },
  admin: {
    useAsTitle: 'title',
    defaultColumns: ['title', 'channels', 'status', 'scheduledAt', 'updatedAt'],
    group: 'Контент',
    description: 'Посты для Telegram, ВКонтакте и MAX. Отправить сразу или в запланированное время.',
  },
  access: {
    read: loggedIn,
    create: ({ req }) => canPost(req.user),
    update: ({ req }) => canPost(req.user),
    delete: ({ req }) => isEditor(req.user),
  },
  hooks: {
    beforeValidate: [
      ({ data }) => {
        if (data && !data.title && data.text) data.title = String(data.text).slice(0, 60)
        return data
      },
    ],
  },
  endpoints: [
    {
      path: '/:id/send',
      method: 'post',
      handler: async (req) => {
        if (!canPost(req.user)) {
          return Response.json({ error: 'Отправлять посты могут SMM и редакторы.' }, { status: 403 })
        }
        const id = req.routeParams?.id as string
        const post = await sendSocialPost(req.payload, id)
        return Response.json({ status: post.status, deliveries: post.deliveries })
      },
    },
  ],
  fields: [
    {
      name: 'title',
      label: 'Название',
      type: 'text',
      admin: { description: 'Для списка в редакции; в соцсети не уходит. По умолчанию — начало текста.' },
    },
    {
      name: 'text',
      label: 'Текст поста',
      type: 'textarea',
      required: true,
      admin: {
        description: 'Лимиты: Telegram — 4096 знаков (1024 с картинкой), MAX — 4000, ВКонтакте — 16 000.',
      },
    },
    { name: 'image', label: 'Картинка', type: 'upload', relationTo: 'media' },
    {
      name: 'article',
      label: 'Материал',
      type: 'relationship',
      relationTo: 'articles',
      admin: { description: 'Ссылка на материал добавится к посту, если задан SITE_URL.' },
    },
    { name: 'link', label: 'Своя ссылка', type: 'text', admin: { description: 'Вместо ссылки на материал.' } },
    {
      name: 'channels',
      label: 'Куда отправить',
      type: 'select',
      hasMany: true,
      required: true,
      options: channelOptions,
    },
    {
      name: 'status',
      label: 'Статус',
      type: 'select',
      defaultValue: 'draft',
      options: [
        { label: 'Черновик', value: 'draft' },
        { label: 'Запланирован', value: 'scheduled' },
        { label: 'Отправляется', value: 'sending' },
        { label: 'Отправлен', value: 'sent' },
        { label: 'Отправлен частично', value: 'partial' },
        { label: 'Ошибка', value: 'failed' },
      ],
      admin: {
        position: 'sidebar',
        description: 'Поставьте «Запланирован» и время — пост уйдёт сам.',
      },
    },
    {
      name: 'scheduledAt',
      label: 'Время отправки',
      type: 'date',
      admin: { position: 'sidebar', date: { pickerAppearance: 'dayAndTime' } },
    },
    {
      name: 'sendButton',
      type: 'ui',
      admin: { position: 'sidebar', components: { Field: '@/components/SendButton#SendButton' } },
    },
    {
      name: 'deliveries',
      label: 'Отправки',
      type: 'array',
      admin: { readOnly: true },
      fields: [
        { name: 'channel', label: 'Канал', type: 'select', options: channelOptions },
        { name: 'ok', label: 'Успешно', type: 'checkbox' },
        { name: 'url', label: 'Ссылка на пост', type: 'text' },
        { name: 'externalId', label: 'ID в соцсети', type: 'text' },
        { name: 'error', label: 'Ошибка', type: 'text' },
        { name: 'sentAt', label: 'Когда', type: 'date' },
      ],
    },
  ],
}
