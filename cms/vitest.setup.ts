// Load .env, then point the tests at their own database and keep the scheduler off.
import 'dotenv/config'

process.env.DATABASE_URL =
  process.env.TEST_DATABASE_URL || 'postgres://payload:payload@127.0.0.1:5432/newsroom_test'
process.env.PAYLOAD_SECRET ||= 'test-secret'
process.env.DISABLE_JOBS = '1'
delete process.env.GITHUB_TOKEN
