export default function Logo({ size = 36 }: { size?: number }) {
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      className="shrink-0 drop-shadow-[0_0_18px_rgba(255,87,34,0.35)]"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="logoBg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1a1a1a" />
          <stop offset="100%" stopColor="#000" />
        </linearGradient>
        <linearGradient id="logoX" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#FFB088" />
          <stop offset="55%" stopColor="#FF7A3D" />
          <stop offset="100%" stopColor="#E64A19" />
        </linearGradient>
      </defs>
      <rect
        width="64"
        height="64"
        rx="14"
        fill="url(#logoBg)"
        stroke="#2a2a2a"
        strokeWidth="1"
      />
      <path
        d="M19 19 L45 45 M45 19 L19 45"
        stroke="url(#logoX)"
        strokeWidth="7"
        strokeLinecap="round"
      />
      <circle cx="51" cy="13" r="2.5" fill="#FF7A3D" />
    </svg>
  );
}

export function Wordmark({ size = 36 }: { size?: number }) {
  return (
    <div className="flex items-center gap-2.5">
      <Logo size={size} />
      <span className="text-lg font-bold tracking-tight">
        Shopify<span className="text-orange-500">Sift</span>
      </span>
    </div>
  );
}
