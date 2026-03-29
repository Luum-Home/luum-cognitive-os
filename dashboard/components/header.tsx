interface HeaderProps {
  title: string;
  description?: string;
}

export function Header({ title, description }: HeaderProps) {
  return (
    <div>
      <h1 className="text-2xl font-bold">{title}</h1>
      {description && (
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          {description}
        </p>
      )}
    </div>
  );
}
