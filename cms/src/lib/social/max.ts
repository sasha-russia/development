import { type ChannelAdapter } from './types'

// MAX Bot API. The bot must be an administrator of the channel. MAX's certificate is
// issued by the Russian Trusted Root CA, so the server needs it in NODE_EXTRA_CA_CERTS.
const API = 'https://platform-api2.max.ru'

export const max: ChannelAdapter = {
  channel: 'max',
  label: 'MAX',
  env: ['MAX_BOT_TOKEN', 'MAX_CHAT_ID'],
  maxLength: 4000,
  async send(post) {
    const body: Record<string, unknown> = { text: post.text }
    if (post.link) {
      body.attachments = [
        {
          type: 'inline_keyboard',
          payload: { buttons: [[{ type: 'link', text: 'Читать на сайте', url: post.link }]] },
        },
      ]
    }

    const res = await fetch(`${API}/messages?chat_id=${encodeURIComponent(process.env.MAX_CHAT_ID!)}`, {
      method: 'POST',
      headers: { Authorization: process.env.MAX_BOT_TOKEN!, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = (await res.json().catch(() => ({}))) as {
      message?: { body?: { mid?: string }; url?: string }
      message_text?: string
      code?: string
    }
    if (!res.ok || !data.message) {
      return { ok: false, error: data.message_text ?? data.code ?? `HTTP ${res.status}` }
    }
    return { ok: true, externalId: data.message.body?.mid, url: data.message.url }
  },
}
