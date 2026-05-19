type ErrorStateProps = {
  message: string;
};

export function ErrorState({ message }: ErrorStateProps) {
  return (
    <div className="rounded-[28px] border border-[var(--color-danger)]/20 bg-[var(--color-danger-soft)] px-6 py-5 text-sm text-[var(--color-danger)]">
      {message}
    </div>
  );
}
