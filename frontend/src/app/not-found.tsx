import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-[calc(100vh-9rem)] items-center justify-center py-10">
      <section className="relative w-full max-w-4xl overflow-hidden rounded-[36px] border border-slate-200/70 bg-slate-950 px-6 py-10 text-slate-50 shadow-[0_40px_120px_rgba(2,8,23,0.45)] sm:px-10 sm:py-12">
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(232,93,42,0.28),transparent_24%),radial-gradient(circle_at_bottom_right,rgba(56,189,248,0.18),transparent_28%),linear-gradient(135deg,rgba(15,23,42,1),rgba(2,6,23,0.96))]"
        />
        <div
          aria-hidden="true"
          className="absolute inset-y-8 left-1/2 hidden w-px bg-white/10 lg:block"
        />

        <div className="relative grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:gap-10">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.38em] text-orange-300">
              Error 404
            </p>
            <h1 className="mt-4 max-w-xl text-4xl font-semibold tracking-[-0.06em] text-white sm:text-5xl">
              La pagina que buscas no existe o ya no esta disponible.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-slate-200">
              Lo sentimos. Es posible que la URL sea incorrecta, que el recurso
              se haya movido o que hayas llegado desde un enlace antiguo.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-100"
                href="/"
              >
                Volver al inicio
              </Link>
              <Link
                className="rounded-full border border-white/18 bg-white/8 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/14"
                href="/correos"
              >
                Ir a correos
              </Link>
              <Link
                className="rounded-full border border-white/18 bg-white/8 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/14"
                href="/lotes"
              >
                Ir a lotes
              </Link>
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-[28px] border border-white/10 bg-white/6 p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.26em] text-slate-300">
                Que puedes hacer ahora
              </p>
              <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-100">
                <li>Revisa que la direccion escrita en el navegador sea correcta.</li>
                <li>Vuelve al inicio para empezar una nueva subida desde la raiz.</li>
                <li>Accede a los listados de correos o lotes si buscabas un analisis ya creado.</li>
              </ul>
            </div>

            <div className="rounded-[28px] border border-orange-400/20 bg-orange-500/10 p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.26em] text-orange-200">
                Nota
              </p>
              <p className="mt-4 text-sm leading-6 text-orange-50">
                Si has llegado aqui desde un marcador antiguo o una ruta guardada
                previamente, vuelve al inicio y navega de nuevo desde la barra superior.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
