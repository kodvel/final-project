import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/visualization-data')({
  component: VisualizationDataPage,
})

function VisualizationDataPage() {
  return <main className="p-8">Visualization Data</main>
}
