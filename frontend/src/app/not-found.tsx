import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4 space-y-4">
      <div className="w-12 h-12 rounded-xl bg-crimson/10 border border-crimson/30 flex items-center justify-center text-crimson font-mono font-bold text-lg">
        404
      </div>
      <h2 className="font-heading font-bold text-2xl text-fg">Page Not Found</h2>
      <p className="text-sm text-muted max-w-md">
        The requested resource or page does not exist in Sift.
      </p>
      <Link
        href="/sources"
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate border border-graphite text-xs font-mono text-electric hover:text-fg transition-colors mt-2"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Return to Sources
      </Link>
    </div>
  );
}

