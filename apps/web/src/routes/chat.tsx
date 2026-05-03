import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/chat')({
  component: ChatPage,
})

function ChatPage() {
  return <main className="p-8">Chat</main>
}
