import { useEffect, useRef, useState } from 'react'
import { Button, Card, ErrorBanner, PageTitle } from '../components/ui.jsx'
import { api, errorMessage } from '../lib/api.js'

function threadId() {
  const key = 'placepilot_thread'
  let id = localStorage.getItem(key)
  if (!id) {
    id = `web-${crypto.randomUUID()}`
    localStorage.setItem(key, id)
  }
  return id
}

export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function onSubmit(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    setError(null)
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setBusy(true)
    try {
      const reply = await api.chat(text, threadId())
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: reply.reply, tools: reply.tools },
      ])
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col">
      <PageTitle>AI Assistant</PageTitle>
      <ErrorBanner message={error} />
      <Card className="mb-4 h-[28rem] overflow-y-auto">
        {messages.length === 0 ? (
          <p className="text-sm text-slate-500">
            Ask about drives, eligibility, stipends, or placement policy.
          </p>
        ) : (
          <ul className="space-y-4">
            {messages.map((msg, idx) => (
              <li key={idx} className={msg.role === 'user' ? 'text-right' : 'text-left'}>
                <div
                  className={`inline-block max-w-[85%] whitespace-pre-wrap rounded-lg px-4 py-2 text-sm ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-100 text-slate-800'
                  }`}
                >
                  {msg.content}
                </div>
                {msg.tools && msg.tools.length > 0 && (
                  <p className="mt-1 text-xs text-slate-400">tools: {msg.tools.join(', ')}</p>
                )}
              </li>
            ))}
          </ul>
        )}
        {busy && <p className="mt-3 text-sm text-slate-400">Thinking…</p>}
        <div ref={bottomRef} />
      </Card>
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the placement assistant…"
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        />
        <Button type="submit" disabled={busy || !input.trim()}>
          Send
        </Button>
      </form>
    </div>
  )
}