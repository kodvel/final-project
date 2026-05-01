import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: HomePage,
})

export function HomePage() {
  return (
    <main className="shell">
      <section className="card">
        <p className="eyebrow">Foundation template</p>
        <h1>Final Project</h1>
        <p>TanStack Start frontend, FastAPI backend, and placeholder contracts for future RAG and AI Agent work.</p>
      </section>
    </main>
  )
}
