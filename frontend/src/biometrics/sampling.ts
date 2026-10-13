export interface Shot<T> {
  item: T;
  at: number;
}

export function spread<T>(items: T[], count: number): T[] {
  if (count <= 0) return [];
  if (items.length <= count) return [...items];
  if (count === 1) return [items[items.length - 1]!];
  const last = items.length - 1;
  return Array.from({ length: count }, (_, i) => items[Math.round((i * last) / (count - 1))]!);
}

export function pickShots<T>(shots: Shot<T>[], detectedAt: number | null, max: number, lookBackMs: number): T[] {
  if (shots.length <= max) return shots.map((s) => s.item);
  if (detectedAt === null) return spread(shots, max).map((s) => s.item);
  const pivot = detectedAt - lookBackMs;
  const recent = shots.filter((s) => s.at >= pivot).slice(0, max);
  const earlier = shots.filter((s) => s.at < pivot);
  return [...spread(earlier, max - recent.length), ...recent].map((s) => s.item);
}
