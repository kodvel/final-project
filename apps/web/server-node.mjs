import { readFile, stat } from 'node:fs/promises'
import { extname, join, normalize } from 'node:path'
import { serve } from 'srvx/node'
import handler from './dist/server/server.js'

const CLIENT_DIR = './dist/client'

const MIME = {
  '.js': 'application/javascript',
  '.mjs': 'application/javascript',
  '.css': 'text/css',
  '.html': 'text/html',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.map': 'application/json',
}

async function tryStatic(pathname) {
  const safe = normalize(pathname).replace(/^(\.\.[\\/])+/g, '')
  const filePath = join(CLIENT_DIR, safe)
  try {
    const s = await stat(filePath)
    if (!s.isFile()) return null
    const data = await readFile(filePath)
    const mime = MIME[extname(filePath)] || 'application/octet-stream'
    const immutable = /[.-][a-f0-9]{8,}\./i.test(filePath)
    return new Response(data, {
      headers: {
        'content-type': mime,
        'cache-control': immutable ? 'public, max-age=31536000, immutable' : 'public, max-age=0, must-revalidate',
      },
    })
  } catch {
    return null
  }
}

const server = serve({
  fetch: async (request) => {
    const url = new URL(request.url)
    const staticRes = await tryStatic(url.pathname)
    if (staticRes) return staticRes
    return handler.fetch(request)
  },
  port: Number(process.env.PORT) || 3000,
  hostname: process.env.HOST || '0.0.0.0',
})

await server.ready()
console.log(`Web server listening on ${server.url}`)
