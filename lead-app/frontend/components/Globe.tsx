"use client";

import { useEffect, useRef } from "react";
import createGlobe from "cobe";

/**
 * Rotierender 3D-Globus (WebGL via cobe) mit Standort-Markern.
 * Leichtgewichtig und ohne schwere 3D-Frameworks – läuft auch mobil flüssig.
 */
export default function Globe() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let phi = 0;
    let width = 0;
    const onResize = () => {
      if (canvasRef.current) width = canvasRef.current.offsetWidth;
    };
    window.addEventListener("resize", onResize);
    onResize();

    const globe = createGlobe(canvasRef.current!, {
      devicePixelRatio: 2,
      width: width * 2,
      height: width * 2,
      phi: 0,
      theta: 0.28,
      dark: 1,
      diffuse: 1.2,
      mapSamples: 16000,
      mapBrightness: 6,
      baseColor: [0.28, 0.3, 0.55],
      markerColor: [0.06, 0.85, 0.55],
      glowColor: [0.25, 0.3, 0.7],
      markers: [
        { location: [52.3759, 9.732], size: 0.1 }, // Hannover
        { location: [52.52, 13.405], size: 0.05 }, // Berlin
        { location: [48.137, 11.575], size: 0.05 }, // München
        { location: [50.937, 6.96], size: 0.05 }, // Köln
        { location: [53.551, 9.993], size: 0.05 }, // Hamburg
      ],
      onRender: (state) => {
        state.phi = phi;
        phi += 0.005;
        state.width = width * 2;
        state.height = width * 2;
      },
    });

    return () => {
      globe.destroy();
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <div className="relative mx-auto aspect-square w-full max-w-[420px]">
      <div className="absolute inset-0 animate-glow rounded-full bg-indigo-500/20 blur-3xl" />
      <canvas
        ref={canvasRef}
        className="relative h-full w-full"
        style={{ contain: "layout paint size" }}
      />
    </div>
  );
}
