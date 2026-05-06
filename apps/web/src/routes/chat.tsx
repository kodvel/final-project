import { createFileRoute } from '@tanstack/react-router'
import { Bot, ChevronRight, Eye, FileSpreadsheet, FileText, Lightbulb, Mic, Paperclip, Send, Workflow, X } from 'lucide-react'
import { type FormEvent, type ReactNode, useState } from 'react'

export const Route = createFileRoute('/chat')({
  component: ChatPage,
})

type Message = { id: number; role: 'user'; content: string } | { id: number; role: 'assistant'; content: AssistantContent }

type AssistantContent = {
  answer: string
  interpretation: string
  recommendation: string
}

const INITIAL_MESSAGES: Message[] = [
  {
    id: 1,
    role: 'user',
    content: 'Can you analyze the Q2 revenue data against enterprise client feedback and generate a decision brief for next quarter?',
  },
  {
    id: 2,
    role: 'assistant',
    content: {
      answer:
        'Based on the synthesis of financial data and client sentiment, there is a clear correlation between the recent feature rollout and a slight dip in Q2 enterprise renewals, despite overall revenue growth.',
      interpretation:
        'The feedback indicates that the new UI introduced in Q1 increased onboarding time for established enterprise users, leading to friction during renewal discussions in Q2. However, net-new logo revenue offset the churn, explaining the top-line growth.',
      recommendation:
        'Deploy targeted enablement resources for existing enterprise accounts and consider a temporary “legacy view” toggle to ease transition friction for Q3 renewals.',
    },
  },
]

const MOCK_ASSISTANT: AssistantContent = {
  answer:
    'The current Source set points to a strategy gap between enterprise adoption and onboarding readiness. Revenue remains healthy, but expansion risk is concentrated in high-touch accounts.',
  interpretation:
    'Enterprise feedback suggests the product direction is viable, but rollout timing and enablement depth need adjustment before the next renewal cycle. The available evidence supports focused mitigation rather than a broad roadmap reversal.',
  recommendation:
    'Prioritize account-specific onboarding assets, add weekly renewal-risk review, and use the next Decision Brief to validate whether enterprise retention risk is declining.',
}

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES)
  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const value = input.trim()
    if (!value || isThinking) return

    const userMessage: Message = { id: Date.now(), role: 'user', content: value }
    setMessages((current) => [...current, userMessage])
    setInput('')
    setIsThinking(true)

    window.setTimeout(() => {
      setMessages((current) => [...current, { id: Date.now() + 1, role: 'assistant', content: MOCK_ASSISTANT }])
      setIsThinking(false)
    }, 800)
  }

  return (
    <div className="grid h-full min-h-0 grid-cols-[minmax(0,1fr)_376px] overflow-hidden text-[#111827]">
      <section className="flex min-h-0 min-w-0 flex-col border-r border-[#E8EAEF]">
        <div className="min-h-0 flex-1 overflow-y-auto px-10 py-8">
          <p className="mb-7 text-center font-[family-name:var(--font-mono)] text-xs font-semibold uppercase tracking-[0.24em] text-[#9CA3AF]">
            Session started: Oct 24, 09:41 AM
          </p>

          <div className="mx-auto max-w-[850px] space-y-8">
            {messages.map((message) =>
              message.role === 'user' ? (
                <UserBubble key={message.id} content={message.content} />
              ) : (
                <AssistantCard key={message.id} content={message.content} />
              ),
            )}

            {isThinking && (
              <div className="flex items-center gap-3 text-sm text-[#6B7280]">
                <div className="grid h-8 w-8 place-items-center rounded-lg bg-[#EEF2FF] text-[#4F46E5]">
                  <Bot className="h-4 w-4" />
                </div>
                Intelligence Copilot is synthesizing Sources...
              </div>
            )}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="shrink-0 border-t border-[#E8EAEF] bg-white px-8 py-5">
          <div className="mx-auto max-w-[850px]">
            <div className="flex items-center gap-3 rounded-2xl border border-[#E8EAEF] bg-white px-4 py-3 shadow-sm">
              <button type="button" className="text-[#9CA3AF] hover:text-[#4F46E5]" aria-label="Attach Source">
                <Paperclip className="h-5 w-5" />
              </button>
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Ask a strategic question or type '/'"
                className="min-w-0 flex-1 border-0 bg-transparent text-sm text-[#111827] outline-none placeholder:text-[#6B7280]"
              />
              <button type="button" className="text-[#9CA3AF] hover:text-[#4F46E5]" aria-label="Voice input">
                <Mic className="h-5 w-5" />
              </button>
              <button
                type="submit"
                disabled={!input.trim() || isThinking}
                className="grid h-10 w-10 place-items-center rounded-xl bg-[#4F46E5] text-white transition hover:bg-[#3525cd] disabled:cursor-not-allowed disabled:opacity-50"
                aria-label="Send message"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-3 flex items-center gap-3 text-xs text-[#9CA3AF]">
              <CommandChip command="/brief" label="Generate Brief" />
              <CommandChip command="/sources" label="View Sources" />
              <CommandChip command="/trace" label="View Trace" />
              <span className="ml-auto">Copilot can make mistakes. Consider verifying.</span>
            </div>
          </div>
        </form>
      </section>

      <SourcesPanel />
    </div>
  )
}

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[65%] rounded-[16px_16px_4px_16px] bg-[#E8E8F8] px-5 py-4 text-sm leading-7 text-[#111827] shadow-sm">{content}</div>
    </div>
  )
}

function AssistantCard({ content }: { content: AssistantContent }) {
  return (
    <article>
      <div className="mb-5 flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-lg bg-[#EEF2FF] text-[#4F46E5]">
          <Bot className="h-5 w-5" />
        </div>
        <h2 className="font-[family-name:var(--font-heading)] text-lg font-semibold text-[#111827]">Intelligence Copilot</h2>
      </div>

      <div className="rounded-2xl border border-[#E8EAEF] bg-white p-8 shadow-sm">
        <div className="border-l-4 border-[#C3C0FF] pl-7">
          <p className="text-sm leading-7 text-[#111827]">{content.answer}</p>

          <div className="mt-7 rounded-xl border border-[#E8EAEF] bg-[#F9FAFB] p-5">
            <div className="mb-4 flex items-center gap-2 text-sm font-medium text-[#6B7280]">
              <FileText className="h-4 w-4" />
              Cited Evidence
            </div>
            <div className="flex flex-wrap gap-3">
              <EvidenceChip icon="csv" label="Q2-Revenue.csv" />
              <EvidenceChip icon="pdf" label="Enterprise_Feedback.pdf" />
            </div>
          </div>

          <p className="mt-7 text-sm leading-7 text-[#111827]">{content.interpretation}</p>

          <div className="mt-7 rounded-xl border border-[#DAD7FF] bg-[#EEF2FF] p-5">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[#4F46E5]">
              <Lightbulb className="h-4 w-4" />
              Recommended Action
            </div>
            <p className="text-sm leading-6 text-[#111827]">{content.recommendation}</p>
          </div>

          <div className="mt-7 grid grid-cols-3 gap-3">
            <ActionButton icon={<Eye className="h-4 w-4" />} label="View Sources" />
            <ActionButton icon={<Workflow className="h-4 w-4" />} label="View Trace" />
            <button
              type="button"
              className="flex items-center justify-center gap-2 rounded-lg bg-[#4F46E5] px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-[#3525cd]"
            >
              <FileText className="h-4 w-4" />
              Generate Decision Brief
            </button>
          </div>
        </div>
      </div>
    </article>
  )
}

function EvidenceChip({ icon, label }: { icon: 'csv' | 'pdf'; label: string }) {
  const Icon = icon === 'csv' ? FileSpreadsheet : FileText
  const color = icon === 'csv' ? 'text-[#16A34A]' : 'text-[#DC2626]'
  return (
    <span className="inline-flex items-center gap-2 rounded-lg border border-[#E8EAEF] bg-white px-3 py-2 font-[family-name:var(--font-mono)] text-xs text-[#111827] shadow-sm">
      <Icon className={`h-4 w-4 ${color}`} />
      {label}
    </span>
  )
}

function ActionButton({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <button
      type="button"
      className="flex items-center justify-center gap-2 rounded-lg border border-[#E8EAEF] bg-white px-4 py-3 text-sm font-semibold text-[#111827] shadow-sm hover:bg-[#F9FAFB]"
    >
      {icon}
      {label}
    </button>
  )
}

function CommandChip({ command, label }: { command: string; label: string }) {
  return (
    <span>
      <span className="rounded bg-[#F4F4F5] px-2 py-1 font-[family-name:var(--font-mono)] text-[#9CA3AF]">{command}</span> {label}
    </span>
  )
}

function SourcesPanel() {
  return (
    <aside className="flex min-h-0 flex-col bg-[#F9FAFB]">
      <div className="flex items-center justify-between border-b border-[#E8EAEF] bg-white px-6 py-6">
        <h2 className="font-[family-name:var(--font-heading)] text-xl font-semibold text-[#111827]">Sources Used</h2>
        <button className="text-[#9CA3AF] hover:text-[#111827]" type="button" aria-label="Close sources panel">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 space-y-5 overflow-auto p-6">
        <SourceCard
          type="pdf"
          name="Q3_Fin PDF"
          badge="p.12"
          quote="Enterprise renewal rates dipped 4% YoY in Q2, primarily attributed to extended onboarding cycles."
        />
        <SourceCard type="csv" name="CRM_Pi CSV" badge="Row 42" quote="[Data Point]: Churn Reason - UI Complexity. Count: 14 Enterprise Accounts." />
      </div>

      <div className="border-t border-[#E8EAEF] bg-white px-6 py-5">
        <PanelLink label="Trace Reference" />
        <PanelLink label="Drafted Briefs" />
      </div>
    </aside>
  )
}

function SourceCard({ type, name, badge, quote }: { type: 'pdf' | 'csv'; name: string; badge: string; quote: string }) {
  const Icon = type === 'pdf' ? FileText : FileSpreadsheet
  const color = type === 'pdf' ? 'text-[#DC2626]' : 'text-[#16A34A]'
  return (
    <article className="rounded-xl border border-[#E8EAEF] bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <Icon className={`h-4 w-4 shrink-0 ${color}`} />
          <h3 className="truncate text-sm font-semibold text-[#111827]">{name}</h3>
        </div>
        <span className="rounded bg-[#F3F4F6] px-2 py-1 font-[family-name:var(--font-mono)] text-[11px] text-[#9CA3AF]">{badge}</span>
      </div>
      <blockquote className="border-l-2 border-[#E8EAEF] pl-4 text-sm italic leading-6 text-[#6B7280]">“{quote}”</blockquote>
    </article>
  )
}

function PanelLink({ label }: { label: string }) {
  return (
    <button className="flex w-full items-center justify-between py-3 text-sm font-medium text-[#111827] hover:text-[#4F46E5]" type="button">
      {label}
      <ChevronRight className="h-4 w-4" />
    </button>
  )
}
