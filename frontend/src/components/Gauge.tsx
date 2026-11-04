// Полукруглый индикатор доли обработанных рисков
export function Gauge({ value, label }: { value: number; label: string }) {
  const clamped = Math.max(0, Math.min(100, value));
  const angle = Math.PI * (1 - clamped / 100);
  const x = 60 + 48 * Math.cos(angle);
  const y = 60 - 48 * Math.sin(angle);
  const large = clamped > 50 ? 1 : 0;
  return (
    <svg viewBox="0 0 120 70" className="gauge" role="img"
         aria-label={`${label} ${clamped}%`}>
      <path d="M12 60 A48 48 0 0 1 108 60" className="gauge-track" />
      {clamped > 0 && (
        <path d={`M12 60 A48 48 0 ${large} 1 ${x.toFixed(2)} ${y.toFixed(2)}`}
              className="gauge-value" />
      )}
      <text x="60" y="52" textAnchor="middle" className="gauge-text">
        {clamped}%
      </text>
      <text x="60" y="67" textAnchor="middle" className="gauge-label">
        {label}
      </text>
    </svg>
  );
}
