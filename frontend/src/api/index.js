import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE || '/api'

const http = axios.create({
  baseURL,
  timeout: 60000
})

export const analyze = (payload) =>
  http.post('/analyze', payload).then((res) => res.data)

export const getReport = (reportId) =>
  http.get(`/reports/${encodeURIComponent(reportId)}`).then((res) => res.data)

export const runBatch = (payload) =>
  http.post('/batch', payload).then((res) => res.data)

export const exportReport = (reportId, format = 'pdf') =>
  http.post('/export', { report_id: reportId, format }).then((res) => res.data)

export const ocrImage = (file) => {
  const form = new FormData()
  form.append('file', file)
  return http.post('/ocr', form, { timeout: 60000 }).then((res) => res.data)
}

/**
 * SSE 分析：POST /analyze/stream，逐条解析 event: progress / report / error。
 * 不用 EventSource，因为它只支持 GET；这里用 fetch 读取流。
 */
export async function analyzeStream(payload, handlers = {}) {
  const response = await fetch(`${baseURL}/analyze/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!response.ok || !response.body) {
    throw new Error(`SSE 连接失败（${response.status}）`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() || ''

    for (const chunk of chunks) {
      let event = 'message'
      const dataLines = []
      for (const line of chunk.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
      }
      if (!dataLines.length) continue

      let data
      try {
        data = JSON.parse(dataLines.join('\n'))
      } catch {
        continue
      }

      if (event === 'progress') handlers.onProgress?.(data)
      else if (event === 'report') handlers.onReport?.(data)
      else if (event === 'error') throw new Error(data.message || '分析失败')
    }
  }
}
