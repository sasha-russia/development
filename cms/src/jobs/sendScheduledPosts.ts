import type { TaskConfig } from 'payload'
import { sendSocialPost } from '@/lib/social'

// Runs every minute and sends posts whose scheduled time has come.
export const sendScheduledPosts: TaskConfig<{ input: Record<string, never>; output: { sent: number } }> = {
  slug: 'sendScheduledPosts',
  label: 'Отправка запланированных постов',
  schedule: [{ cron: '0 * * * * *', queue: 'social' }],
  retries: 0,
  handler: async ({ req }) => {
    const due = await req.payload.find({
      collection: 'social-posts',
      where: {
        and: [
          { status: { equals: 'scheduled' } },
          { scheduledAt: { less_than_equal: new Date().toISOString() } },
        ],
      },
      limit: 20,
      depth: 0,
      overrideAccess: true,
    })
    for (const post of due.docs) {
      await sendSocialPost(req.payload, post.id)
    }
    return { output: { sent: due.docs.length } }
  },
}
