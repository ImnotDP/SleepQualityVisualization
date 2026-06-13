/**
 * Static file server + API proxy for sleep-quality frontend.
 * Reads ports from ../backend/config.txt.
 * Zero external dependencies (Node.js built-ins only).
 *
 * Usage: node serve.js
 */

const http = require('http')
const fs = require('fs')
const path = require('path')

// ---------- read config ----------
function loadConfig() {
  const cfg = {}
  const configPath = path.join(__dirname, '..', 'backend', 'config.txt')
  try {
    const content = fs.readFileSync(configPath, 'utf-8')
    content.split(/\r?\n/).forEach(line => {
      const m = line.match(/^([^#].*?)=(.*)/)
      if (m) cfg[m[1].trim()] = m[2].trim()
    })
  } catch (_) { /* fall back to defaults */ }
  return cfg
}

const config = loadConfig()
const PORT = parseInt(config['FRONTEND_PORT'], 10) || 3000
const BACKEND_HOST = '127.0.0.1'
const BACKEND_PORT = parseInt(config['FLASK_PORT'], 10) || 5000
const DIST_DIR = path.join(__dirname, 'dist')

// 检查 dist 目录是否存在
if (!fs.existsSync(DIST_DIR)) {
  console.error('dist not found, run: npm run build')
  process.exit(1)
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript',
  '.mjs': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
}

function serveFile(res, filePath) {
  const ext = path.extname(filePath).toLowerCase()
  const contentType = MIME[ext] || 'application/octet-stream'

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' })
      res.end('404 Not Found')
    } else {
      res.writeHead(200, { 'Content-Type': contentType })
      res.end(data)
    }
  })
}

function proxyRequest(req, res) {
  const options = {
    hostname: BACKEND_HOST,
    port: BACKEND_PORT,
    path: req.url,
    method: req.method,
    headers: { ...req.headers, host: BACKEND_HOST + ':' + BACKEND_PORT },
  }

  const proxy = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers)
    proxyRes.pipe(res)
  })

  proxy.on('error', () => {
    res.writeHead(502, { 'Content-Type': 'text/plain; charset=utf-8' })
    res.end('502 Bad Gateway — 后端服务未启动，请确认 Flask 正在运行')
  })

  req.pipe(proxy)
}

const server = http.createServer((req, res) => {
  // API 请求代理到 Flask 后端
  if (req.url.startsWith('/api/')) {
    proxyRequest(req, res)
    return
  }

  // 静态文件 + SPA 回退
  let urlPath = req.url.split('?')[0]
  if (urlPath === '/') urlPath = '/index.html'

  let filePath = path.join(DIST_DIR, urlPath)

  fs.stat(filePath, (err, stats) => {
    if (err || stats.isDirectory()) {
      // SPA fallback：所有非文件路径返回 index.html
      filePath = path.join(DIST_DIR, 'index.html')
    }
    serveFile(res, filePath)
  })
})

server.listen(PORT, () => {
  console.log('http://localhost:' + PORT)
})
