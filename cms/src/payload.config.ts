import { postgresAdapter } from '@payloadcms/db-postgres'
import { lexicalEditor } from '@payloadcms/richtext-lexical'
import { ru } from '@payloadcms/translations/languages/ru'
import path from 'path'
import { buildConfig } from 'payload'
import sharp from 'sharp'
import { fileURLToPath } from 'url'

import { Articles } from './collections/Articles'
import { Media } from './collections/Media'
import { SocialPosts } from './collections/SocialPosts'
import { Tasks } from './collections/Tasks'
import { Users } from './collections/Users'
import { sendScheduledPosts } from './jobs/sendScheduledPosts'
import { migrations } from './migrations'

const filename = fileURLToPath(import.meta.url)
const dirname = path.dirname(filename)

export default buildConfig({
  serverURL: process.env.SERVER_URL || '',
  admin: {
    user: Users.slug,
    importMap: { baseDir: path.resolve(dirname) },
    meta: { titleSuffix: ' — Редакция' },
    components: { beforeDashboard: ['@/components/Dashboard#Dashboard'] },
  },
  i18n: { supportedLanguages: { ru }, fallbackLanguage: 'ru' },
  collections: [Articles, SocialPosts, Tasks, Media, Users],
  editor: lexicalEditor(),
  secret: process.env.PAYLOAD_SECRET || '',
  // The static site's build fetches published articles from the REST API.
  cors: process.env.SITE_URL ? [new URL(process.env.SITE_URL).origin] : [],
  typescript: { outputFile: path.resolve(dirname, 'payload-types.ts') },
  db: postgresAdapter({
    pool: { connectionString: process.env.DATABASE_URL || '' },
    // In development the schema syncs automatically; in production these run on start.
    prodMigrations: migrations,
  }),
  jobs: {
    tasks: [sendScheduledPosts],
    // Runs the scheduler inside the server process; set DISABLE_JOBS=1 for one-off scripts.
    autoRun: [{ cron: '* * * * *', queue: 'social' }],
    shouldAutoRun: () => !process.env.DISABLE_JOBS,
  },
  sharp,
  plugins: [],
})
