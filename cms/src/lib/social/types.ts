export type Channel = 'telegram' | 'vk' | 'max'

export type OutgoingPost = {
  text: string
  link?: string
  image?: { data: Buffer; filename: string; mimeType: string }
}

export type DeliveryResult = {
  channel: Channel
  ok: boolean
  externalId?: string
  url?: string
  error?: string
}

export type ChannelAdapter = {
  channel: Channel
  label: string
  // Env variables the adapter needs; listed in the admin when something is missing.
  env: string[]
  maxLength: number
  send: (post: OutgoingPost) => Promise<Omit<DeliveryResult, 'channel'>>
}

export function missingEnv(names: string[]): string[] {
  return names.filter((name) => !process.env[name])
}

export function withLink(text: string, link?: string): string {
  return link ? `${text}\n\n${link}` : text
}
