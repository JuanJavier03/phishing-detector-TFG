"use client";

type SpinnerProps = {
  size?: "sm" | "md" | "lg";
  className?: string;
};

const sizeClasses = {
  sm: "h-4 w-4 border-2",
  md: "h-6 w-6 border-[3px]",
  lg: "h-10 w-10 border-4",
};

export function Spinner({ size = "md", className = "" }: SpinnerProps) {
  return (
    <div
      aria-hidden="true"
      className={`animate-spin rounded-full border-[var(--color-accent-soft)] border-t-[var(--color-accent)] ${sizeClasses[size]} ${className}`.trim()}
    />
  );
}
