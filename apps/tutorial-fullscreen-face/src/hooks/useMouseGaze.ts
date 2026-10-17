import { useCallback, useEffect, useMemo, useState } from "react";
import {
  mapNormalizedControlValue,
  resolveFaceControls,
  useVizijRuntime,
} from "@vizij/runtime-react";

function clamp(value: number, min = -1, max = 1) {
  return Math.min(Math.max(value, min), max);
}

type GazeOptions = {
  flipX?: boolean;
  flipY?: boolean;
  /** Logs missing eye controls and the first few writes. Turn off when done debugging. */
  debug?: boolean;
};

export function useMouseGaze(
  enabled: boolean,
  { flipX = false, flipY = false, debug = false }: GazeOptions = {},
): (node: HTMLDivElement | null) => void {
  const {
    setInput,
    faceId: runtimeFaceId,
    assetBundle,
    inputConstraints,
  } = useVizijRuntime();

  // Track the element in state (via a callback ref) so the effect re-runs
  // when the div actually mounts, instead of silently bailing on a null ref.
  const [target, setTarget] = useState<HTMLDivElement | null>(null);
  const ref = useCallback((node: HTMLDivElement | null) => {
    setTarget(node);
  }, []);

  const controls = useMemo(
    () => resolveFaceControls(assetBundle, runtimeFaceId, inputConstraints),
    [assetBundle, inputConstraints, runtimeFaceId],
  );

  useEffect(() => {
    if (!enabled || !target) {
      return;
    }

    if (debug) {
      console.log("[gaze] attached to", target, "eyes:", controls.eyes);
    }

    let logged = 0;
    const warned = new Set<string>();

    const setEye = (path: keyof typeof controls.eyes, value: number) => {
      const control = controls.eyes[path];
      if (!control) {
        if (debug && !warned.has(path)) {
          warned.add(path);
          console.warn(`[gaze] no control found for eyes.${String(path)}`);
        }
        return;
      }
      const mapped = mapNormalizedControlValue(control, clamp(value));
      if (debug && logged < 8) {
        logged += 1;
        console.log("[gaze] set", control.path, mapped);
      }
      setInput(control.path, { float: mapped });
    };

    const handlePointer = (event: PointerEvent) => {
      const rect = target.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) {
        return;
      }
      const xRatio = (event.clientX - rect.left) / rect.width;
      const yRatio = (event.clientY - rect.top) / rect.height;
      const normalizedX = clamp((xRatio * 2 - 1) * (flipX ? -1 : 1));
      const normalizedY = clamp(((1 - yRatio) * 2 - 1) * (flipY ? -1 : 1));

      setEye("leftX", normalizedX);
      setEye("rightX", normalizedX);
      setEye("leftY", normalizedY);
      setEye("rightY", normalizedY);
    };

    // Eyes recenter only when the pointer leaves the face area.
    // (Previously `pointerup` also reset, which snapped the eyes to center on every click.)
    const reset = () => {
      setEye("leftX", 0);
      setEye("leftY", 0);
      setEye("rightX", 0);
      setEye("rightY", 0);
    };

    target.addEventListener("pointermove", handlePointer, true);
    target.addEventListener("pointerdown", handlePointer, true);
    target.addEventListener("pointerleave", reset);

    return () => {
      target.removeEventListener("pointermove", handlePointer, true);
      target.removeEventListener("pointerdown", handlePointer, true);
      target.removeEventListener("pointerleave", reset);
    };
  }, [controls, enabled, target, setInput, flipX, flipY, debug]);

  return ref;
}
