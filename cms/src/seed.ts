// Usage: npm run seed       — creates the first administrator from SEED_ADMIN_*
//        npm run seed:demo  — also demo staff, the site's demo articles, a task and a post
import path from 'path'
import { getPayload } from 'payload'
import { fileURLToPath } from 'url'
import config from './payload.config'

const dirname = path.dirname(fileURLToPath(import.meta.url))
const siteRoot = path.resolve(dirname, '../..')

function lexical(paragraphs: string[]) {
  return {
    root: {
      type: 'root',
      format: '' as const,
      indent: 0,
      version: 1,
      direction: 'ltr' as const,
      children: paragraphs.map((text) => ({
        type: 'paragraph',
        format: '' as const,
        indent: 0,
        version: 1,
        direction: 'ltr' as const,
        textFormat: 0,
        children: [{ type: 'text', text, format: 0, detail: 0, mode: 'normal', style: '', version: 1 }],
      })),
    },
  }
}

async function ensureUser(
  payload: Awaited<ReturnType<typeof getPayload>>,
  data: { email: string; password: string; name: string; role: 'admin' | 'editor' | 'journalist' | 'smm'; position?: string },
) {
  const existing = await payload.find({ collection: 'users', where: { email: { equals: data.email } }, limit: 1 })
  if (existing.docs[0]) return { user: existing.docs[0], created: false }
  return { user: await payload.create({ collection: 'users', data }), created: true }
}

async function main() {
  const payload = await getPayload({ config })
  const email = process.env.SEED_ADMIN_EMAIL
  const password = process.env.SEED_ADMIN_PASSWORD
  if (!email || !password) throw new Error('Set SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD')

  const admin = await ensureUser(payload, { email, password, name: 'Администратор', role: 'admin' })
  payload.logger.info(`Admin ${email}: ${admin.created ? 'created' : 'already exists'}`)

  if (!process.env.SEED_DEMO) process.exit(0)

  const demoPassword = process.env.SEED_DEMO_PASSWORD || password
  const editor = await ensureUser(payload, { email: 'editor@example.com', password: demoPassword, name: 'Анна Редакторова', role: 'editor', position: 'Главный редактор' })
  const journalist = await ensureUser(payload, { email: 'journalist@example.com', password: demoPassword, name: 'Иван Корреспондентов', role: 'journalist', position: 'Корреспондент' })
  await ensureUser(payload, { email: 'smm@example.com', password: demoPassword, name: 'Мария Постова', role: 'smm', position: 'SMM-редактор' })

  // The site's demo content lives in the site project.
  const { demoArticles: articles } = await import(path.join(siteRoot, 'src/lib/news.ts'))
  const mediaBySrc = new Map<string, number>()

  for (const a of articles) {
    const exists = await payload.find({ collection: 'articles', where: { slug: { equals: a.slug } }, limit: 1 })
    if (exists.docs[0]) continue

    let photo: number | undefined
    if (a.photo) {
      photo = mediaBySrc.get(a.photo.src)
      if (!photo) {
        const media = await payload.create({
          collection: 'media',
          data: { alt: a.photo.alt, credit: a.photo.credit, sourceUrl: a.photo.page },
          filePath: path.join(siteRoot, 'public', a.photo.src),
        })
        photo = media.id
        mediaBySrc.set(a.photo.src, photo)
      }
    }

    await payload.create({
      collection: 'articles',
      data: {
        title: a.title,
        slug: a.slug,
        lead: a.lead,
        format: a.format,
        photo,
        body: a.body.length ? lexical(a.body) : undefined,
        cards: a.cards,
        questions: a.questions?.map((q: { text: string; options: string[]; answer: number; explanation: string }) => ({
          text: q.text,
          options: q.options.map((text) => ({ text })),
          answer: q.answer + 1,
          explanation: q.explanation,
        })),
        duration: a.duration,
        featured: a.featured ?? false,
        author: journalist.user.id,
        publishedAt: a.publishedAt,
        _status: 'published',
      },
    })
  }

  const tasks = await payload.find({ collection: 'tasks', limit: 1 })
  if (!tasks.docs.length) {
    const article = await payload.find({ collection: 'articles', where: { slug: { equals: 'five-storey' } }, limit: 1 })
    await payload.create({
      collection: 'tasks',
      data: {
        title: 'Дописать историю про пятиэтажки: комментарий администрации',
        description: 'Запросить комментарий у отдела капремонта, добавить в текст до вечера.',
        status: 'in_progress',
        priority: 'urgent',
        assignee: journalist.user.id,
        dueDate: new Date(Date.now() + 6 * 3600 * 1000).toISOString(),
        article: article.docs[0]?.id,
        createdBy: editor.user.id,
      },
    })
    await payload.create({
      collection: 'social-posts',
      data: {
        text: 'Набережную откроют после реконструкции 1 ноября. Рассказываем, что на ней изменилось.',
        article: (await payload.find({ collection: 'articles', where: { slug: { equals: 'embankment-opening' } }, limit: 1 })).docs[0]?.id,
        channels: ['telegram', 'vk', 'max'],
        status: 'draft',
      },
    })
  }

  payload.logger.info(`Demo data ready. Staff passwords: ${process.env.SEED_DEMO_PASSWORD ? 'SEED_DEMO_PASSWORD' : 'same as admin'}`)
  process.exit(0)
}

try {
  await main()
} catch (error) {
  console.error(error)
  process.exit(1)
}
