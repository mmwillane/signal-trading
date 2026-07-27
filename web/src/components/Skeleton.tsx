export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton rounded-2xl ${className}`} />;
}

export function CardSkeleton() {
  return (
    <div className="bezel">
      <div className="bezel-core p-5 space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-6 w-24" />
          <Skeleton className="h-6 w-16" />
        </div>
        <Skeleton className="h-9 w-full" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-5 w-20" />
        </div>
      </div>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="bezel">
      <div className="bezel-core p-6 text-center">
        <p className="text-sm" style={{ color: "var(--color-rose)" }}>
          {message}
        </p>
        <p className="mt-2 text-xs" style={{ color: "var(--color-faint)" }}>
          Vérifie que le backend (port 8010) est démarré.
        </p>
      </div>
    </div>
  );
}
