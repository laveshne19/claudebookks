export function Logo({ className = "", light = false }: { className?: string; light?: boolean }) {
  return (
    <span className={`flex items-center gap-2.5 ${className}`}>
      <svg width="36" height="36" viewBox="0 0 48 48" fill="none" className="shrink-0">
        <rect x="6" y="18" width="36" height="24" rx="3" fill={light ? "#15795A" : "#0E5C43"} stroke="#C9A227" strokeWidth="1.6" />
        <rect x="6" y="18" width="36" height="7" rx="2" fill="#C9A227" />
        <rect x="21.5" y="11" width="5" height="31" fill="#C9A227" />
        <path d="M24 11c-4-6-12-3-9 2 2 3 9-2 9-2Z" fill="#E4C97A" />
        <path d="M24 11c4-6 12-3 9 2-2 3-9-2-9-2Z" fill="#E4C97A" />
        <circle cx="24" cy="11" r="2.3" fill="#0A3F2E" stroke="#C9A227" strokeWidth="1.2" />
      </svg>
      <span className={`font-display text-xl font-semibold tracking-tight ${light ? "text-white" : "text-emerald"}`}>
        BizWrap<span className="text-gold"> India</span>
      </span>
    </span>
  );
}
