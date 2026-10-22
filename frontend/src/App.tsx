import { useEffect, useState } from 'react'

type Health = { status: string }

export function App() {
  const [status, setStatus] = useState('Bağlantı kontrol ediliyor…')

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 5000)
    async function checkHealth() {
      try {
        const response = await fetch('/api/health', { signal: controller.signal })
        if (!response.ok) throw new Error('Health request failed')
        const health: Health = await response.json()
        if (health.status !== 'ok') throw new Error('Unexpected health response')
        if (active) setStatus('API erişilebilir')
      } catch {
        if (active) {
          setStatus(controller.signal.aborted ? 'API kontrolü zaman aşımına uğradı' : 'API bağlantısı kurulamadı')
        }
      } finally {
        window.clearTimeout(timeout)
      }
    }
    void checkHealth()
    return () => {
      active = false
      controller.abort()
      window.clearTimeout(timeout)
    }
  }, [])

  return (
    <main className="mx-auto max-w-4xl px-6 py-16">
      <p className="text-sm font-semibold tracking-widest text-emerald-700">BYTEME · AVATAR 2026</p>
      <h1 className="mt-4 text-4xl font-bold tracking-tight text-slate-900">Üretimden satışa, kayıtlı ve izlenebilir.</h1>
      <p className="mt-6 max-w-2xl text-lg text-slate-600">
        Gıda üretimi, maliyet, satış ve lot izlenebilirliği prototipinin geliştirme temeli.
      </p>
      <section className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm" aria-labelledby="status-heading">
        <h2 id="status-heading" className="text-xl font-semibold">Sistem durumu</h2>
        <p className="mt-3 text-slate-700" role="status">{status}</p>
        <p className="mt-3 text-sm text-slate-500">Bu kontrol yalnızca API erişimini gösterir. İş akışları ve veritabanı hazırlığı ayrıca doğrulanmalıdır.</p>
      </section>
      <p className="mt-8 text-sm text-slate-500">Üretim, parçalama, satış, geri çağırma ve tahmin modülleri sonraki geliştirme aşamasındadır.</p>
    </main>
  )
}
