import { type ChannelAdapter, withLink } from './types'

const CAPTION_LIMIT = 1024

// Bot API: the bot must be an administrator of the channel with "Post messages".
export const telegram: ChannelAdapter = {
  channel: 'telegram',
  label: 'Telegram',
  env: ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'],
  maxLength: 4096,
  async send(post) {
    const token = process.env.TELEGRAM_BOT_TOKEN!
    const chatId = process.env.TELEGRAM_CHAT_ID!
    const text = withLink(post.text, post.link)
    const api = `https://api.telegram.org/bot${token}`

    let res: Response
    if (post.image && text.length <= CAPTION_LIMIT) {
      const form = new FormData()
      form.append('chat_id', chatId)
      form.append('caption', text)
      form.append(
        'photo',
        new Blob([new Uint8Array(post.image.data)], { type: post.image.mimeType }),
        post.image.filename,
      )
      res = await fetch(`${api}/sendPhoto`, { method: 'POST', body: form })
    } else {
      res = await fetch(`${api}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: chatId, text }),
      })
    }

    const body = (await res.json()) as {
      ok: boolean
      description?: string
      result?: { message_id: number }
    }
    if (!body.ok || !body.result) return { ok: false, error: body.description ?? `HTTP ${res.status}` }

    const id = String(body.result.message_id)
    const url = chatId.startsWith('@') ? `https://t.me/${chatId.slice(1)}/${id}` : undefined
    return { ok: true, externalId: id, url }
  },
}
