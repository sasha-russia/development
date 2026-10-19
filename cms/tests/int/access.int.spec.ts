import { getPayload, type Payload } from 'payload'
import { beforeAll, describe, expect, it } from 'vitest'
import config from '@/payload.config'
import type { User } from '@/payload-types'

let payload: Payload
const staff: Record<'admin' | 'editor' | 'journalist' | 'otherJournalist' | 'smm', User> = {} as never

async function makeUser(role: User['role'], email: string) {
  const found = await payload.find({ collection: 'users', where: { email: { equals: email } } })
  if (found.docs[0]) return found.docs[0]
  return payload.create({ collection: 'users', data: { email, password: 'test-pass-123', name: email, role } })
}

const as = (user: User) => ({ user, overrideAccess: false as const })

beforeAll(async () => {
  payload = await getPayload({ config: await config })
  for (const collection of ['tasks', 'social-posts', 'articles'] as const) {
    await payload.delete({ collection, where: { id: { exists: true } } })
  }
  staff.admin = await makeUser('admin', 'admin@test.local')
  staff.editor = await makeUser('editor', 'editor@test.local')
  staff.journalist = await makeUser('journalist', 'journalist@test.local')
  staff.otherJournalist = await makeUser('journalist', 'journalist2@test.local')
  staff.smm = await makeUser('smm', 'smm@test.local')
})

describe('articles', () => {
  it('lets a journalist save a draft but not publish it', async () => {
    const draft = await payload.create({
      collection: 'articles',
      data: { title: 'Черновик журналиста', lead: 'Лид', format: 'news' },
      draft: true,
      ...as(staff.journalist),
    })
    expect(draft.slug).toBe('chernovik-zhurnalista')
    expect((draft.author as User).id ?? draft.author).toBe(staff.journalist.id)

    await expect(
      payload.update({
        collection: 'articles',
        id: draft.id,
        data: { _status: 'published' },
        ...as(staff.journalist),
      }),
    ).rejects.toThrow(/только редактор/)
  })

  it('lets an editor publish, and hides drafts from anonymous readers', async () => {
    const article = await payload.create({
      collection: 'articles',
      data: { title: 'Новость редактора', lead: 'Лид', format: 'news', _status: 'published' },
      ...as(staff.editor),
    })
    expect(article._status).toBe('published')
    expect(article.publishedAt).toBeTruthy()

    const anon = await payload.find({ collection: 'articles', overrideAccess: false })
    expect(anon.docs.map((a) => a.title)).toEqual(['Новость редактора'])
  })

  it("stops a journalist from editing someone else's article", async () => {
    const other = await payload.create({
      collection: 'articles',
      data: { title: 'Чужой материал', lead: 'Лид', format: 'news' },
      draft: true,
      ...as(staff.otherJournalist),
    })
    await expect(
      payload.update({ collection: 'articles', id: other.id, data: { title: 'Правка' }, ...as(staff.journalist) }),
    ).rejects.toThrow()
  })
})

describe('tasks', () => {
  it('shows a journalist only their own tasks and does not let them reassign', async () => {
    const mine = await payload.create({
      collection: 'tasks',
      data: { title: 'Моя задача', assignee: staff.journalist.id, status: 'new' },
      ...as(staff.editor),
    })
    await payload.create({
      collection: 'tasks',
      data: { title: 'Чужая задача', assignee: staff.otherJournalist.id, status: 'new' },
      ...as(staff.editor),
    })

    const visible = await payload.find({ collection: 'tasks', ...as(staff.journalist) })
    expect(visible.docs.map((t) => t.title)).toEqual(['Моя задача'])
    expect(mine.createdBy).toMatchObject({ id: staff.editor.id })

    const updated = await payload.update({
      collection: 'tasks',
      id: mine.id,
      data: { status: 'in_progress', assignee: staff.otherJournalist.id },
      ...as(staff.journalist),
    })
    expect(updated.status).toBe('in_progress')
    expect((updated.assignee as User).id).toBe(staff.journalist.id)
  })
})

describe('social posts and users', () => {
  it('lets SMM create posts but not journalists', async () => {
    const post = await payload.create({
      collection: 'social-posts',
      data: { text: 'Пост', channels: ['telegram'] },
      ...as(staff.smm),
    })
    expect(post.title).toBe('Пост')
    await expect(
      payload.create({ collection: 'social-posts', data: { text: 'Нет', channels: ['vk'] }, ...as(staff.journalist) }),
    ).rejects.toThrow()
  })

  it('only lets admins create staff and change roles', async () => {
    await expect(
      payload.create({
        collection: 'users',
        data: { email: 'x@test.local', password: 'test-pass-123', name: 'X', role: 'editor' },
        ...as(staff.editor),
      }),
    ).rejects.toThrow()

    const self = await payload.update({
      collection: 'users',
      id: staff.journalist.id,
      data: { role: 'admin', position: 'Корреспондент' },
      ...as(staff.journalist),
    })
    expect(self.role).toBe('journalist')
    expect(self.position).toBe('Корреспондент')
  })
})
