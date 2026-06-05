"use client";

// 3D-Globus aus reinem CSS (3D-Transforms) – rendert überall sichtbar,
// ohne WebGL. Rotierendes Drahtgitter über einer leuchtenden Kugel.

const MERIDIANS = [0, 30, 60, 90, 120, 150];
const MARKERS = [
  { top: "30%", left: "45%" },
  { top: "45%", left: "61%" },
  { top: "58%", left: "39%" },
  { top: "39%", left: "31%" },
];

export default function Globe() {
  return (
    <div
      className="relative mx-auto aspect-square w-full max-w-[440px]"
      style={{ perspective: "1100px" }}
    >
      {/* weicher Glow */}
      <div className="absolute inset-[5%] animate-glow rounded-full bg-indigo-500/30 blur-3xl" />

      {/* solider, schattierter Kern */}
      <div
        className="absolute inset-[14%] rounded-full"
        style={{
          background:
            "radial-gradient(circle at 34% 28%, #a5b4fc 0%, #6366f1 38%, #312e81 70%, #14122e 100%)",
          boxShadow:
            "inset -18px -22px 55px rgba(0,0,0,0.55), inset 10px 10px 30px rgba(199,210,254,0.25), 0 0 70px rgba(99,102,241,0.35)",
        }}
      />

      {/* rotierendes Drahtgitter (echtes CSS-3D) */}
      <div
        className="absolute inset-[14%]"
        style={{ transformStyle: "preserve-3d", animation: "globeSpin 18s linear infinite" }}
      >
        {MERIDIANS.map((deg) => (
          <div
            key={deg}
            className="absolute inset-0 rounded-full border border-indigo-200/25"
            style={{ transform: `rotateY(${deg}deg)` }}
          />
        ))}
        <div
          className="absolute inset-0 rounded-full border border-emerald-300/30"
          style={{ transform: "rotateX(90deg)" }}
        />
        <div
          className="absolute inset-0 rounded-full border border-indigo-200/15"
          style={{ transform: "rotateX(65deg)" }}
        />
        <div
          className="absolute inset-0 rounded-full border border-indigo-200/15"
          style={{ transform: "rotateX(115deg)" }}
        />
      </div>

      {/* Glanzlicht oben links */}
      <div className="absolute left-[26%] top-[22%] h-[14%] w-[14%] rounded-full bg-white/50 blur-md" />

      {/* leuchtende Standort-Marker */}
      {MARKERS.map((m, i) => (
        <span key={i} className="absolute" style={{ top: m.top, left: m.left }}>
          <span className="absolute -inset-2 animate-ping rounded-full bg-emerald-400/40" />
          <span className="block h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_10px_2px_rgba(16,185,129,0.7)]" />
        </span>
      ))}
    </div>
  );
}
