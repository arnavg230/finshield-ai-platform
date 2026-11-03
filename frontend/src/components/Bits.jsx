// Small shared pieces used across the screens.

export function PageHead({ title, subtitle, children }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children && <div className="row-actions">{children}</div>}
    </div>
  );
}

export function Level({ value }) {
  return <span className={`level level-${value}`}>{value}</span>;
}

export function Money({ value }) {
  return (
    <span className="num">
      {Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 })}
    </span>
  );
}

export function Score({ value }) {
  if (value === null || value === undefined) return <span className="dim">—</span>;
  return <span className="num">{Number(value).toFixed(3)}</span>;
}

export function Notice({ children, bad }) {
  if (!children) return null;
  return <div className={bad ? "notice bad" : "notice"}>{children}</div>;
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}

export function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
