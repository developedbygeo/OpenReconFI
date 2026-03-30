async function waitForService(url: string, label: string, timeoutMs = 30_000) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url)
      if (res.ok) return
    } catch {
      // not ready yet
    }
    await new Promise((r) => setTimeout(r, 1000))
  }
  throw new Error(
    `${label} at ${url} did not respond within ${timeoutMs / 1000}s. Is the Docker stack running? Run: docker compose up -d`,
  )
}

export default async function globalSetup() {
  await Promise.all([
    waitForService('http://localhost:3000', 'Frontend'),
    waitForService('http://localhost:8000/docs', 'Backend'),
  ])
}
