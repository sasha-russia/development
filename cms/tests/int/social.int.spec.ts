import { getPayload, type Payload } from 'payload'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import config from '@/payload.config'
import { deliver, sendSocialPost } from '@/lib/social'

let payload: Payload

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

beforeAll(async () => {
  payload = await getPayload({ config: await config })
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe('channel adapters', () => {
  it('reports a channel without credentials instead of calling it', async () => {
    vi.stubEnv('TELEGRAM_BOT_TOKEN', '')
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const result = await deliver('telegram', { text: 'Привет' })
    expect(result).toMatchObject({ ok: false, error: expect.stringContaining('TELEGRAM_BOT_TOKEN') })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('posts to a public Telegram channel and builds the post link', async () => {
    vi.stubEnv('TELEGRAM_BOT_TOKEN', 'tg-token')
    vi.stubEnv('TELEGRAM_CHAT_ID', '@city_news')
    const fetchMock = vi.fn().mockResolvedValue(json({ ok: true, result: { message_id: 42 } }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await deliver('telegram', { text: 'Новость', link: 'https://site/news/a/' })

    expect(result).toEqual({ channel: 'telegram', ok: true, externalId: '42', url: 'https://t.me/city_news/42' })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('https://api.telegram.org/bottg-token/sendMessage')
    expect(JSON.parse(init.body)).toEqual({ chat_id: '@city_news', text: 'Новость\n\nhttps://site/news/a/' })
  })

  it('passes VK errors through', async () => {
    vi.stubEnv('VK_ACCESS_TOKEN', 'vk-token')
    vi.stubEnv('VK_GROUP_ID', '-123')
    const fetchMock = vi.fn().mockResolvedValue(json({ error: { error_code: 15, error_msg: 'Access denied' } }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await deliver('vk', { text: 'Пост', link: 'https://site/x/' })

    expect(result).toEqual({ channel: 'vk', ok: false, error: '15: Access denied' })
    const body = fetchMock.mock.calls[0][1].body as URLSearchParams
    expect(body.get('owner_id')).toBe('-123')
    expect(body.get('attachments')).toBe('https://site/x/')
  })

  it('sends to MAX with the token in the Authorization header and a link button', async () => {
    vi.stubEnv('MAX_BOT_TOKEN', 'max-token')
    vi.stubEnv('MAX_CHAT_ID', '-7001')
    const fetchMock = vi
      .fn()
      .mockResolvedValue(json({ message: { body: { mid: 'mid.1' }, url: 'https://max.ru/c/1/mid.1' } }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await deliver('max', { text: 'Пост', link: 'https://site/x/' })

    expect(result).toMatchObject({ ok: true, externalId: 'mid.1', url: 'https://max.ru/c/1/mid.1' })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('https://platform-api2.max.ru/messages?chat_id=-7001')
    expect(init.headers.Authorization).toBe('max-token')
    expect(JSON.parse(init.body).attachments[0].payload.buttons[0][0].url).toBe('https://site/x/')
  })

  it('rejects text over the channel limit', async () => {
    vi.stubEnv('MAX_BOT_TOKEN', 'max-token')
    vi.stubEnv('MAX_CHAT_ID', '1')
    vi.stubGlobal('fetch', vi.fn())
    const result = await deliver('max', { text: 'я'.repeat(4001) })
    expect(result).toMatchObject({ ok: false, error: expect.stringContaining('4000') })
  })
})

describe('sendSocialPost', () => {
  it('records partial delivery and resends only the failed channel', async () => {
    vi.stubEnv('TELEGRAM_BOT_TOKEN', 'tg-token')
    vi.stubEnv('TELEGRAM_CHAT_ID', '-100500')
    vi.stubEnv('VK_ACCESS_TOKEN', 'vk-token')
    vi.stubEnv('VK_GROUP_ID', '123')

    const post = await payload.create({
      collection: 'social-posts',
      data: { text: 'Анонс', channels: ['telegram', 'vk'] },
    })

    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) =>
        url.includes('telegram')
          ? json({ ok: true, result: { message_id: 7 } })
          : json({ error: { error_code: 5, error_msg: 'User authorization failed' } }),
      ),
    )
    const first = await sendSocialPost(payload, post.id)
    expect(first.status).toBe('partial')
    expect(first.deliveries?.map((d) => [d.channel, d.ok])).toEqual([
      ['telegram', true],
      ['vk', false],
    ])

    const retryFetch = vi.fn(async () => json({ response: { post_id: 99 } }))
    vi.stubGlobal('fetch', retryFetch)
    const second = await sendSocialPost(payload, post.id)
    expect(retryFetch).toHaveBeenCalledTimes(1)
    expect(second.status).toBe('sent')
    expect(second.deliveries?.find((d) => d.channel === 'vk')?.url).toBe('https://vk.com/wall-123_99')
  })
})
