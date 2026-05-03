import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/source-data')({
  component: SourceDataPage,
})

function SourceDataPage() {
  return <main className="p-8">Source Data</main>
}
