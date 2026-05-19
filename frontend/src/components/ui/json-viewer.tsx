type JsonViewerProps = {
  value: unknown;
};

export function JsonViewer({ value }: JsonViewerProps) {
  return (
    <pre className="overflow-x-auto rounded-[22px] border border-[var(--color-border)] bg-[#201c19] p-4 font-mono text-xs leading-6 text-[#f4efe7]">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
