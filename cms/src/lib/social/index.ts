import fs from 'fs/promises'
import path from 'path'
import type { Payload } from 'payload'
import { max } from './max'
import { telegram } from './telegram'
import { type Channel, type ChannelAdapter, type DeliveryResult, missingEnv, type OutgoingPost } from './types'
import { vk } from './vk'

export const adapters: Record<Channel, ChannelAdapter> = { telegram, vk, max }

export const channelOptions = Object.values(adapters).map((a) => ({ label: a.label, value: a.channel }))

export function channelStatus() {
  return Object.values(adapters).map((a) => ({
    channel: a.channel,
    label: a.label,
    missing: missingEnv(a.env),
  }))
}

export async function deliver(channel: Channel, post: OutgoingPost): Promise<DeliveryResult> {
  const adapter = adapters[channel]
  const missing = missingEnv(adapter.env)
  if (missing.length) {
    return { channel, ok: false, error: `Канал не подключён: задайте ${missing.join(', ')}` }
  }
  if (post.text.length > adapter.maxLength) {
    return { channel, ok: false, error: `Текст длиннее ${adapter.maxLength} символов` }
  }
  try {
    return { channel, ...(await adapter.send(post)) }
  } catch (error) {
    return { channel, ok: false, error: error instanceof Error ? error.message : String(error) }
  }
}

type MediaDoc = { filename?: string | null; mimeType?: string | null }

async function loadImage(payload: Payload, media: MediaDoc | null | undefined) {
  if (!media?.filename) return undefined
  const dir = payload.collections.media.config.upload.staticDir || 'media'
  const data = await fs.readFile(path.resolve(dir, media.filename))
  return { data, filename: media.filename, mimeType: media.mimeType ?? 'image/jpeg' }
}

function articleUrl(article: { slug?: string | null } | null | undefined): string | undefined {
  const base = process.env.SITE_URL
  if (!base || !article?.slug) return undefined
  return `${base.replace(/\/$/, '')}/news/${article.slug}/`
}

// Sends one post to its chosen channels and records each delivery on the document.
// Channels that already succeeded are skipped, so a retry only resends failures.
export async function sendSocialPost(payload: Payload, id: number | string) {
  const post = await payload.findByID({ collection: 'social-posts', id, depth: 1, overrideAccess: true })
  const previous = (post.deliveries ?? []) as (DeliveryResult & { sentAt?: string })[]
  const done = new Set(previous.filter((d) => d.ok).map((d) => d.channel))
  const pending = ((post.channels ?? []) as Channel[]).filter((c) => !done.has(c))

  await payload.update({
    collection: 'social-posts',
    id,
    data: { status: 'sending' },
    overrideAccess: true,
  })

  const outgoing: OutgoingPost = {
    text: post.text,
    link: post.link || articleUrl(post.article as { slug?: string } | null),
    image: await loadImage(payload, post.image as MediaDoc | null),
  }

  const sentAt = new Date().toISOString()
  const results = await Promise.all(pending.map((channel) => deliver(channel, outgoing)))
  const deliveries = [
    ...previous.filter((d) => d.ok),
    ...results.map((r) => ({ ...r, sentAt })),
  ]
  const allOk = deliveries.length > 0 && deliveries.every((d) => d.ok)
  const anyOk = deliveries.some((d) => d.ok)

  return payload.update({
    collection: 'social-posts',
    id,
    data: { status: allOk ? 'sent' : anyOk ? 'partial' : 'failed', deliveries },
    overrideAccess: true,
  })
}
