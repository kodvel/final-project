import { serve } from 'srvx/node'
import handler from './dist/server/server.js'

const server = serve({
  fetch: handler.fetch,
  port: Number(process.env.PORT) || 3000,
  hostname: process.env.HOST || '0.0.0.0',
})

await server.ready()
console.log(`Web server listening on ${server.url}`)
