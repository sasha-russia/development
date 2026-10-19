import type { Payload } from 'payload'

// Asks GitHub Actions to rebuild the static site. Needs GITHUB_TOKEN (fine-grained,
// "Contents: read and write" on the site repository) and GITHUB_REPO ("owner/name").
export async function requestSiteRebuild(payload: Payload, reason: string): Promise<void> {
  const token = process.env.GITHUB_TOKEN
  const repo = process.env.GITHUB_REPO
  if (!token || !repo) {
    payload.logger.info(`Site rebuild skipped (${reason}): GITHUB_TOKEN or GITHUB_REPO is not set`)
    return
  }

  try {
    const res = await fetch(`https://api.github.com/repos/${repo}/dispatches`, {
      method: 'POST',
      headers: {
        Accept: 'application/vnd.github+json',
        Authorization: `Bearer ${token}`,
        'X-GitHub-Api-Version': '2022-11-28',
      },
      body: JSON.stringify({ event_type: 'cms-publish', client_payload: { reason } }),
    })
    if (!res.ok) {
      payload.logger.error(`Site rebuild request failed: ${res.status} ${await res.text()}`)
      return
    }
    payload.logger.info(`Site rebuild requested: ${reason}`)
  } catch (error) {
    payload.logger.error({ err: error, msg: 'Site rebuild request failed' })
  }
}
