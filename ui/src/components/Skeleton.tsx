export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-gray-200 rounded-md ${className}`} />
  );
}

export function PanelSkeleton() {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <Skeleton className="h-6 w-48 mb-4" />
      <Skeleton className="h-24 w-full mb-4" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}
