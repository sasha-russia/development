import type { Payload } from 'payload'
import { channelStatus } from '@/lib/social'

type Props = { payload: Payload; user?: { id: number | string; name?: string } | null }

const statusLabels: Record<string, string> = {
  new: 'Новая',
  in_progress: 'В работе',
  review: 'На проверке',
}

const box: React.CSSProperties = {
  border: '1px solid var(--theme-elevation-150)',
  borderRadius: 8,
  padding: '16px 20px',
}

// Server component shown above the admin dashboard: my open tasks and channel status.
export async function Dashboard({ payload, user }: Props) {
  const tasks = user
    ? await payload.find({
        collection: 'tasks',
        where: {
          and: [{ assignee: { equals: user.id } }, { status: { not_equals: 'done' } }],
        },
        sort: 'dueDate',
        limit: 10,
        depth: 0,
        overrideAccess: true,
      })
    : null
  const channels = channelStatus()

  return (
    <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', marginBottom: 32 }}>
      <section style={box}>
        <h3 style={{ marginBottom: 12 }}>Мои задачи</h3>
        {!tasks?.docs.length && <p>Открытых задач нет.</p>}
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 8 }}>
          {tasks?.docs.map((task) => (
            <li key={task.id}>
              <a href={`/admin/collections/tasks/${task.id}`}>{task.title}</a>
              <span style={{ color: 'var(--theme-elevation-500)', fontSize: 13 }}>
                {' '}
                · {statusLabels[task.status] ?? task.status}
                {task.dueDate &&
                  ` · до ${new Date(task.dueDate).toLocaleString('ru-RU', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Moscow' })}`}
                {task.priority === 'urgent' && ' · срочно'}
              </span>
            </li>
          ))}
        </ul>
      </section>
      <section style={box}>
        <h3 style={{ marginBottom: 12 }}>Соцсети</h3>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 8 }}>
          {channels.map((c) => (
            <li key={c.channel}>
              <strong>{c.label}:</strong>{' '}
              {c.missing.length ? (
                <span style={{ color: 'var(--theme-error-500)' }}>не подключён (нужно {c.missing.join(', ')})</span>
              ) : (
                <span style={{ color: 'var(--theme-success-500)' }}>подключён</span>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
