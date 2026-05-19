import { Spinner } from "@/components/ui/spinner";

type LoadingStateProps = {
  label: string;
};

export function LoadingState({ label }: LoadingStateProps) {
  return (
    <div className="rounded-[28px] border border-[var(--color-border)] bg-[var(--color-panel)] px-6 py-10 text-center">
      <Spinner className="mx-auto mb-4" size="lg" />
      <p className="text-sm text-[var(--color-muted)]">{label}</p>
    </div>
  );
}
