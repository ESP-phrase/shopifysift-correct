type SearchParams = Promise<{ error?: string; next?: string }>;

export default async function LoginPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { error, next } = await searchParams;
  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_0%_100%,rgba(255,87,34,0.18),transparent_60%),radial-gradient(ellipse_60%_40%_at_100%_0%,rgba(255,87,34,0.10),transparent_60%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[length:32px_32px]" />

      <header className="relative flex items-center justify-between px-12 py-6">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-neutral-800 bg-neutral-950 text-lg font-bold">
            ×
          </div>
          <span className="text-lg font-bold">ShopifySift</span>
        </div>
        <nav className="flex items-center gap-7 text-sm">
          <a href="#" className="text-neutral-400 hover:text-white">
            Pricing
          </a>
          <a href="/login" className="text-neutral-400 hover:text-white">
            Log in
          </a>
          <a
            href="#"
            className="rounded-lg bg-orange-600 px-5 py-2.5 font-semibold text-white shadow-[0_0_24px_rgba(255,87,34,0.4)] hover:bg-orange-500"
          >
            Start free
          </a>
        </nav>
      </header>

      <main className="relative flex justify-center px-6 pt-8 pb-20">
        <div className="w-full max-w-[520px] rounded-2xl border border-orange-950/60 bg-neutral-950/60 p-11 backdrop-blur shadow-[0_0_60px_rgba(255,87,34,0.06)]">
          <div className="mb-3.5 text-center">
            <span className="inline-block rounded-full border border-orange-500/30 bg-orange-500/10 px-3.5 py-1 font-mono text-xs text-orange-500">
              // LOG IN
            </span>
          </div>
          <h1 className="text-center text-[34px] font-bold leading-tight tracking-tight">
            Welcome <span className="text-orange-500">back ✦</span>
          </h1>
          <p className="mt-2.5 mb-7 text-center text-neutral-400">
            Sign in to your ShopifySift dashboard
          </p>

          {error ? (
            <div className="mb-3.5 text-center text-sm text-red-400">
              Invalid email or password.
            </div>
          ) : null}

          <form action="/api/login" method="POST" className="space-y-4">
            {next ? <input type="hidden" name="next" value={next} /> : null}

            <div className="relative">
              <label className="mb-2 block text-[11px] uppercase tracking-[0.1em] text-neutral-400">
                Email
              </label>
              <span className="absolute left-3.5 top-[38px] text-neutral-500">
                ✉
              </span>
              <input
                type="text"
                name="username"
                placeholder="you@example.com"
                autoFocus
                required
                className="w-full rounded-lg border border-neutral-800 bg-neutral-950 px-3.5 py-3.5 pl-11 text-white placeholder:text-neutral-600 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15"
              />
            </div>

            <div className="relative">
              <label className="mb-2 block text-[11px] uppercase tracking-[0.1em] text-neutral-400">
                Password
              </label>
              <span className="absolute left-3.5 top-[38px] text-neutral-500">
                🔒
              </span>
              <input
                type="password"
                name="password"
                placeholder="••••••••"
                required
                className="w-full rounded-lg border border-neutral-800 bg-neutral-950 px-3.5 py-3.5 pl-11 text-white placeholder:text-neutral-600 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15"
              />
            </div>

            <div className="flex items-center justify-between text-sm">
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  name="remember"
                  className="accent-orange-500"
                />
                Remember me
              </label>
              <a href="#" className="text-orange-500 hover:underline">
                Forgot password?
              </a>
            </div>

            <button
              type="submit"
              className="w-full rounded-lg bg-orange-600 px-4 py-3.5 text-[15px] font-semibold text-white shadow-[0_0_30px_rgba(255,87,34,0.45)] hover:bg-orange-500"
            >
              Log in →
            </button>
          </form>

          <div className="my-5 text-center text-[11px] tracking-[0.15em] text-neutral-500">
            — OR CONTINUE WITH —
          </div>

          <div className="grid grid-cols-3 gap-2.5">
            {["Google", "GitHub", "Microsoft"].map((p) => (
              <button
                key={p}
                type="button"
                disabled
                title="Not wired yet"
                className="flex items-center justify-center gap-2 rounded-lg border border-neutral-800 bg-neutral-950 px-2 py-2.5 text-sm text-white opacity-85 cursor-not-allowed"
              >
                {p}
              </button>
            ))}
          </div>

          <div className="mt-5 grid grid-cols-3 gap-3 rounded-xl border border-neutral-900 bg-white/[0.02] p-3.5 text-xs">
            {[
              { h: "5 free searches", t: "to start" },
              { h: "No credit card", t: "required" },
              { h: "Cancel anytime", t: "free tier is forever" },
            ].map((p) => (
              <div key={p.h} className="flex items-start gap-2">
                <span className="text-orange-500">⏵</span>
                <div>
                  <div className="font-semibold text-white">{p.h}</div>
                  <div className="text-neutral-400">{p.t}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-5 text-center text-sm text-neutral-400">
            New here?{" "}
            <a href="#" className="text-orange-500 hover:underline">
              Sign up free
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}
