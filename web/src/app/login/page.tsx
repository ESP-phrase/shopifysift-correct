import { Wordmark } from "@/components/Logo";

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
        <Wordmark size={36} />
        <nav className="flex items-center gap-7 text-sm">
          <a href="#" className="text-neutral-300 hover:text-white">Pricing</a>
          <a href="/login" className="text-neutral-300 hover:text-white">Log in</a>
          <a
            href="#"
            className="rounded-lg bg-orange-500 px-5 py-2.5 font-semibold text-white shadow-[0_0_30px_rgba(255,87,34,0.5)] hover:bg-orange-400"
          >
            Start free
          </a>
        </nav>
      </header>

      <main className="relative flex justify-center px-6 pt-4 pb-20">
        <div className="w-full max-w-[560px] rounded-2xl border border-orange-950/70 bg-neutral-950/60 p-12 backdrop-blur shadow-[0_0_80px_rgba(255,87,34,0.08)]">
          <div className="mb-4 text-center">
            <span className="inline-block rounded-full border border-orange-500/30 bg-orange-500/10 px-3.5 py-1 font-mono text-xs tracking-wider text-orange-500">
              // LOG IN
            </span>
          </div>
          <h1 className="text-center text-[38px] font-bold leading-tight tracking-tight">
            Welcome <span className="text-orange-500">back ✦</span>
          </h1>
          <p className="mt-3 mb-8 text-center text-neutral-400">
            Sign in to your ShopifySift dashboard
          </p>

          {error ? (
            <div className="mb-4 text-center text-sm text-red-400">
              Invalid email or password.
            </div>
          ) : null}

          <form action="/api/login" method="POST" className="space-y-5">
            {next ? <input type="hidden" name="next" value={next} /> : null}

            <Field label="Email" name="username" type="text" placeholder="you@example.com" autoFocus icon={<MailIcon />} />
            <PasswordField />

            <div className="flex items-center justify-between text-sm">
              <label className="flex cursor-pointer select-none items-center gap-2.5">
                <input
                  type="checkbox"
                  name="remember"
                  defaultChecked
                  className="h-4 w-4 cursor-pointer appearance-none rounded border border-neutral-700 bg-neutral-950 checked:border-orange-500 checked:bg-orange-500 checked:bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 16%22><path fill=%22white%22 d=%22M6.5 11L3 7.5 4.4 6 6.5 8.2 11.6 3 13 4.4z%22/></svg>')] checked:bg-center checked:bg-no-repeat"
                />
                Remember me
              </label>
              <a href="#" className="font-medium text-orange-500 hover:underline">
                Forgot password?
              </a>
            </div>

            <button
              type="submit"
              className="w-full rounded-lg bg-orange-500 px-4 py-4 text-[15px] font-semibold text-white shadow-[0_0_40px_rgba(255,87,34,0.55)] transition hover:bg-orange-400"
            >
              Log in →
            </button>
          </form>

          <div className="my-6 text-center text-[11px] tracking-[0.2em] text-neutral-500">
            OR CONTINUE WITH
          </div>

          <div className="grid grid-cols-3 gap-2.5">
            <SocialButton label="Google" icon={<GoogleIcon />} />
            <SocialButton label="GitHub" icon={<GitHubIcon />} />
            <SocialButton label="Microsoft" icon={<MicrosoftIcon />} />
          </div>

          <div className="mt-6 grid grid-cols-3 gap-3 rounded-xl border border-neutral-900 bg-white/[0.02] p-4 text-xs">
            {[
              { h: "5 free searches", t: "to start" },
              { h: "No credit card", t: "required" },
              { h: "Cancel anytime", t: "free tier is forever" },
            ].map((p) => (
              <div key={p.h} className="flex items-start gap-2">
                <CheckIcon />
                <div>
                  <div className="font-semibold text-white">{p.h}</div>
                  <div className="text-neutral-400">{p.t}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 text-center text-sm text-neutral-300">
            New here?{" "}
            <a href="#" className="font-medium text-orange-500 hover:underline">
              Sign up free
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}

function Field({
  label,
  name,
  type,
  placeholder,
  autoFocus,
  icon,
}: {
  label: string;
  name: string;
  type: string;
  placeholder: string;
  autoFocus?: boolean;
  icon: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-2 block text-[11px] font-medium uppercase tracking-[0.12em] text-neutral-400">
        {label}
      </label>
      <div className="relative">
        <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-neutral-500">
          {icon}
        </span>
        <input
          type={type}
          name={name}
          placeholder={placeholder}
          autoFocus={autoFocus}
          required
          className="w-full rounded-lg border border-neutral-800 bg-neutral-950 py-3.5 pl-11 pr-4 text-white placeholder:text-neutral-600 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/20"
        />
      </div>
    </div>
  );
}

function PasswordField() {
  return (
    <div>
      <label className="mb-2 block text-[11px] font-medium uppercase tracking-[0.12em] text-neutral-400">
        Password
      </label>
      <div className="relative">
        <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-orange-500">
          <LockIcon />
        </span>
        <input
          type="password"
          name="password"
          placeholder="••••••••"
          required
          className="w-full rounded-lg border border-neutral-800 bg-neutral-950 py-3.5 pl-11 pr-12 text-white placeholder:text-neutral-600 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/20"
        />
        <button
          type="button"
          tabIndex={-1}
          aria-label="Toggle password visibility"
          className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-1.5 text-neutral-400 hover:text-white"
          onClick={
            // SSR-safe inline toggle
            undefined
          }
        >
          <EyeIcon />
        </button>
      </div>
    </div>
  );
}

function SocialButton({ label, icon }: { label: string; icon: React.ReactNode }) {
  return (
    <button
      type="button"
      title="Not wired yet"
      disabled
      className="flex items-center justify-center gap-2.5 rounded-lg border border-neutral-800 bg-neutral-950 px-3 py-3 text-sm text-white opacity-90 cursor-not-allowed hover:border-neutral-700"
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

function MailIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M3 7l9 6 9-6" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 1 1 8 0v4" />
    </svg>
  );
}

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 flex-none text-orange-500" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 48 48" className="h-5 w-5">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.7-6.1 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 7.9 3l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16 19 13 24 13c3 0 5.8 1.1 7.9 3l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.5-5.2l-6.2-5.2c-2.1 1.5-4.6 2.4-7.3 2.4-5.2 0-9.6-3.3-11.3-7.9l-6.6 5.1C9.6 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.3 4.3-4.3 5.7l6.2 5.2C40.3 35.6 44 30.3 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="white">
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.55v-1.92c-3.2.69-3.87-1.55-3.87-1.55-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.75 2.69 1.24 3.34.95.1-.74.4-1.24.72-1.53-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.18-3.09-.12-.29-.51-1.46.11-3.05 0 0 .96-.31 3.15 1.18a10.97 10.97 0 0 1 5.74 0c2.19-1.49 3.15-1.18 3.15-1.18.62 1.59.23 2.76.11 3.05.74.81 1.18 1.83 1.18 3.09 0 4.42-2.69 5.39-5.25 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.55C20.21 21.39 23.5 17.08 23.5 12 23.5 5.65 18.35.5 12 .5Z" />
    </svg>
  );
}

function MicrosoftIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5">
      <rect x="2" y="2" width="9" height="9" fill="#F25022" />
      <rect x="13" y="2" width="9" height="9" fill="#7FBA00" />
      <rect x="2" y="13" width="9" height="9" fill="#00A4EF" />
      <rect x="13" y="13" width="9" height="9" fill="#FFB900" />
    </svg>
  );
}
