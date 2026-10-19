'use client'

import { Button, toast, useDocumentInfo } from '@payloadcms/ui'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

export function SendButton() {
  const { id } = useDocumentInfo()
  const router = useRouter()
  const [sending, setSending] = useState(false)

  if (!id) {
    return <p style={{ color: 'var(--theme-elevation-500)' }}>Сохраните пост, чтобы его отправить.</p>
  }

  async function send() {
    setSending(true)
    try {
      const res = await fetch(`/api/social-posts/${id}/send`, { method: 'POST', credentials: 'include' })
      const body = await res.json()
      if (!res.ok) {
        toast.error(body.error ?? 'Не удалось отправить')
      } else if (body.status === 'sent') {
        toast.success('Пост отправлен во все выбранные каналы')
      } else {
        const failed = (body.deliveries ?? []).filter((d: { ok: boolean }) => !d.ok)
        toast.error(`Не все каналы приняли пост: ${failed.map((d: { error: string }) => d.error).join('; ')}`)
      }
      router.refresh()
    } finally {
      setSending(false)
    }
  }

  return (
    <div style={{ marginBottom: 'var(--base)' }}>
      <Button buttonStyle="primary" disabled={sending} onClick={send}>
        {sending ? 'Отправляем…' : 'Отправить сейчас'}
      </Button>
      <p style={{ color: 'var(--theme-elevation-500)', fontSize: 13 }}>
        Уйдёт в выбранные каналы; уже отправленные повторно не отправятся. Сохраните изменения перед отправкой.
      </p>
    </div>
  )
}
