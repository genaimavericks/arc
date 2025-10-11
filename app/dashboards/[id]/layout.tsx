// Required for static export with dynamic routes
export async function generateStaticParams() {
  // Return a placeholder - actual routing will be handled client-side
  return [{ id: 'placeholder' }]
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <div>{children}</div>
}
