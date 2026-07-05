// Small formatting helpers shared across components.

export function fmtSpeed(kmh) {
  return `${Math.round(kmh)} km/h`;
}

// Speed with a confidence marker: a leading "~" when the projection was too
// far-court (perspective-amplified) to trust the number as measured.
export function fmtSpeedConf(kmh, confident) {
  return `${confident === false ? "~" : ""}${Math.round(kmh)} km/h`;
}

export function fmtDuration(seconds) {
  const s = Math.max(0, Math.round(seconds));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, "0")}`;
}

export function playerName(match, id) {
  const p = match.players.find((p) => p.id === id);
  return p ? p.name : id;
}

// Title-case a shot type for display.
export function fmtShotType(t) {
  return t.charAt(0).toUpperCase() + t.slice(1);
}

// Full stroke description: spin style (when detected and not flat) + type,
// e.g. "Slice Backhand". `spin_style` is additive in the schema — older
// match.json files simply lack it and fall back to the bare type.
export function fmtStroke(shot) {
  const style = shot.spin_style;
  const base = fmtShotType(shot.type);
  return style && style !== "flat" ? `${fmtShotType(style)} ${base}` : base;
}
