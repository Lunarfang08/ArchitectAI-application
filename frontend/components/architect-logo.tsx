export function ArchitectLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" role="img" aria-label="ArchitectAI mark">
      <path d="M24 2 46 24 24 46 2 24 24 2Z" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M24 8 39 39h-8l-2.8-6H19.7L17 39H9L24 8Zm0 13.2-2.2 5.1h4.5L24 21.2Z" fill="currentColor" />
      <path d="M5 24h38M24 5v8" fill="none" stroke="currentColor" strokeWidth="1" opacity=".45" />
    </svg>
  );
}
