import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: HomePage,
})

export function HomePage() {
  return (
    <main className="flex items-center min-h-screen justify-center p-8">
      <section className="bg-white border border-amber-100 rounded-3xl shadow-xl max-w-3xl w-full p-8">
        <p className="text-amber-700 text-xs font-bold tracking-widest uppercase mb-4">Foundation template</p>
        <h1 className="text-5xl font-bold tracking-tight leading-none mb-4">Final Project</h1>
        <p className="text-lg leading-relaxed m-0">TanStack Start frontend, FastAPI backend, and placeholder contracts for future RAG and AI Agent work.</p>
      </section>
    </main>
  )
}