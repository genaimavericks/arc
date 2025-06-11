// This is the server component file which includes generateStaticParams

import { TransformationPlanClient } from './client-page'

// Define static parameters for Next.js static site generation
// Required for all dynamic routes when using output: export
export function generateStaticParams() {
  // For static export, we need to pre-define routes
  return [{ planId: 'placeholder' }]
}

// Server component that renders the client component
export default function TransformationPlanPage({ params }: { params: { planId: string } }) {
  // Pass the planId from the route params to the client component
  return <TransformationPlanClient planId={params.planId} />
}
