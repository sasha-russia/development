import { type ChannelAdapter } from './types'

const API_VERSION = '5.199'

// wall.post needs a user access token of a community admin with the "wall" scope
// (VK grants it on request via devsupport@corp.vk.com). The post goes out on behalf
// of the community; the article link becomes a link snippet.
export const vk: ChannelAdapter = {
  channel: 'vk',
  label: 'ВКонтакте',
  env: ['VK_ACCESS_TOKEN', 'VK_GROUP_ID'],
  maxLength: 16000,
  async send(post) {
    const groupId = process.env.VK_GROUP_ID!.replace(/^-/, '')
    const params = new URLSearchParams({
      owner_id: `-${groupId}`,
      from_group: '1',
      message: post.text,
      access_token: process.env.VK_ACCESS_TOKEN!,
      v: API_VERSION,
    })
    if (post.link) params.set('attachments', post.link)

    const res = await fetch('https://api.vk.com/method/wall.post', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: params,
    })
    const body = (await res.json()) as {
      response?: { post_id: number }
      error?: { error_code: number; error_msg: string }
    }
    if (!body.response) {
      const err = body.error
      return { ok: false, error: err ? `${err.error_code}: ${err.error_msg}` : `HTTP ${res.status}` }
    }

    const id = String(body.response.post_id)
    return { ok: true, externalId: id, url: `https://vk.com/wall-${groupId}_${id}` }
  },
}
