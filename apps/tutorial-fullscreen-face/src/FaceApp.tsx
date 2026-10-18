import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import type { ChangeEvent } from "react";
import {
  VizijRuntimeProvider,
  VizijRuntimeFace,
  useVizijRuntime,
  resolveFaceControls,
  type VizijAssetBundle,
} from "@vizij/runtime-react";
import { useMouseGaze } from "./hooks/useMouseGaze";
import { usePoseHotkeys, POSE_HOTKEY_LAYOUT } from "./hooks/usePoseHotkeys";
import "./styles.css";

const faceAssetUrl = new URL(
  "../../vizij-authoring/public/assets/Quori_Current_Extended.glb",
  import.meta.url,
).href;

const assetBundle: VizijAssetBundle = {
  namespace: "fullscreen-face",
  glb: {
    kind: "url",
    src: faceAssetUrl,
    aggressiveImport: true,
  },
  pose: {
    stageNeutralFilter: (_id, path) => !path.includes("/color/"),
  },
};

function VizijRuntimeHud() {
  const { loading, error, ready } = useVizijRuntime();
  return (
    <div>
      Status:
      {loading && <div>Loading Face {ready}</div>}
      {error && <div>Error: {error.message}</div>}
      {!ready && <div>Initializing</div>}
    </div>
  );
}

function FaceRuntime() {
  const runtime = useVizijRuntime();
  const {
    ready,
    loading,
    error,
    stagePoseNeutral,
    assetBundle,
    faceId,
    inputConstraints,
  } = runtime;
  const poseConfig = assetBundle.pose?.config ?? null;
  const gazeRef = useMouseGaze(ready, { flipX: true });
  const { bindings } = usePoseHotkeys(poseConfig, ready);
  const [hintsVisible, setHintsVisible] = useState(false);
  const [mappingStatus, setMappingStatus] = useState<string | null>(null);

  const handlePointerMove = useCallback(() => {
    setHintsVisible(true);
  }, []);

  const { setInput } = runtime;
  const [w, setW] = useState(0);
  const firstPose = poseConfig?.poses?.[0];

  const handleMappingFile = useCallback(
    async (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      event.target.value = "";
      if (!file) return;
      try {
        const document = JSON.parse(await file.text()) as {
          controls?: Record<string, unknown>;
          targets?: Record<string, unknown>;
        };
        if (!document.controls || typeof document.controls !== "object") {
          if (document.targets && typeof document.targets === "object") {
            throw new Error(
              "You selected quori_mapping.json, which defines mapping rules. " +
                "Run map_to_quori.py first, then upload the generated *.quori.json file.",
            );
          }
          throw new Error(
            "This JSON is not a Quori result file. Upload a generated *.quori.json file containing controls.",
          );
        }
        const entries = Object.entries(document.controls);
        if (entries.length === 0) {
          throw new Error("The controls object is empty.");
        }
        for (const [path, rawValue] of entries) {
          if (typeof rawValue !== "number" || !Number.isFinite(rawValue)) {
            throw new Error(`Control "${path}" must have a finite number.`);
          }
          setInput(path, { float: rawValue });
          const controlMatch = new RegExp(
            `^rig/${faceId}/(.+?)/value$`,
          ).exec(path);
          if (controlMatch) {
            const controlId = controlMatch[1]?.split("/").join("_");
            if (controlId?.startsWith("brow_")) {
              setInput(`rig/${faceId}/override/${controlId}/enabled`, {
                float: 1,
              });
              setInput(`rig/${faceId}/override/${controlId}/value`, {
                float: rawValue,
              });
            }
          }
        }
        const overrideCount = entries.filter(([path]) =>
          path.includes("/brow/"),
        ).length;
        setMappingStatus(
          `Applied ${entries.length} Quori controls` +
            (overrideCount > 0
              ? ` (${overrideCount} brow overrides enabled).`
              : "."),
        );
      } catch (error) {
        setMappingStatus(
          error instanceof Error ? error.message : "Could not apply mapping.",
        );
      }
    },
    [faceId, setInput],
  );

  useEffect(() => {
    if (!ready || !firstPose) return;
    const path = `rig/${faceId}/poses/${firstPose.id}.weight`;
    console.log("setting", path, w);
    console.log(
      "POSE:",
      firstPose.name,
      JSON.stringify(firstPose.values, null, 2),
    );
    setInput(path, { float: w });
  }, [w, ready, firstPose, faceId, setInput]);

  useEffect(() => {
    if (ready) {
      stagePoseNeutral();
    }
  }, [ready, stagePoseNeutral]);

  // Auto-play motion graph from bundle metadata when ?autoplay is present
  const autoPlayTriggeredRef = useRef(false);
  useEffect(() => {
    if (!ready || loading) return;
    if (autoPlayTriggeredRef.current) return;
    const params = new URLSearchParams(window.location.search);
    if (!params.has("autoplay")) return;
    const meta = assetBundle.bundle?.metadata as
      | Record<string, unknown>
      | undefined;
    const activeId: string | undefined =
      typeof meta?.activeMotionGraphId === "string"
        ? meta.activeMotionGraphId
        : Array.isArray(meta?.activeMotionGraphIds) &&
            typeof (meta.activeMotionGraphIds as unknown[])[0] === "string"
          ? ((meta.activeMotionGraphIds as unknown[])[0] as string)
          : undefined;
    if (!activeId) return;
    const match = (assetBundle.programs ?? []).find((p) => p.id === activeId);
    if (!match) return;
    try {
      runtime.playProgram(activeId);
      autoPlayTriggeredRef.current = true;
    } catch {
      // will retry on next render cycle
    }
  }, [ready, loading, assetBundle, runtime.playProgram]);

  const hotkeyHints = useMemo(() => {
    if (!poseConfig || bindings.length === 0) {
      return [];
    }
    return bindings.slice(0, POSE_HOTKEY_LAYOUT.length).map((binding, idx) => ({
      key: POSE_HOTKEY_LAYOUT[idx]?.label ?? `${idx + 1}`,
      label: binding.pose.name ?? `Pose ${idx + 1}`,
      semanticKey: binding.semanticKey,
    }));
  }, [bindings, poseConfig]);

  const controls = useMemo(
    () => resolveFaceControls(assetBundle, faceId, inputConstraints),
    [assetBundle, faceId, inputConstraints],
  );

  useEffect(() => {
    if (!ready) return;
    console.log("KEYS:", Object.keys(controls));
    console.log("ALL CONTROLS:", controls);
    try {
      console.log("CONTROLS JSON:\n" + JSON.stringify(controls, null, 2));
    } catch {
      console.log(
        "controls not JSON-serializable, expand ALL CONTROLS instead",
      );
    }
  }, [ready, controls]);

  if (loading) {
    return (
      <div className="fullscreen">
        <div className="status">Loading face…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fullscreen">
        <div className="status error hud-error">{error.message}</div>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="fullscreen">
        <div className="status">Initialising runtime…</div>
      </div>
    );
  }

  return (
    <div className="fullscreen" onPointerMove={handlePointerMove}>
      <div ref={gazeRef} className="canvas-wrapper">
        <VizijRuntimeFace className="face-canvas" showSafeArea={false} />
      </div>
      {hintsVisible && (
        <div className="hint">
          <div>Move the mouse to steer gaze.</div>
          <div>Press the hotkeys to trigger poses:</div>
          {hotkeyHints.length > 0 ? (
            <ul>
              {hotkeyHints.map((entry) => (
                <li key={entry.key}>
                  <kbd>{entry.key}</kbd> → {entry.label}
                </li>
              ))}
            </ul>
          ) : (
            <div>Bundle did not include a pose rig with hotkeys.</div>
          )}
        </div>
      )}
      <label
        style={{
          position: "fixed",
          right: 20,
          bottom: 20,
          zIndex: 10,
          padding: 10,
          background: "rgba(0, 0, 0, 0.65)",
        }}
      >
        Apply generated Quori controls JSON
        <div style={{ marginTop: 4, maxWidth: 280, fontSize: 12 }}>
          Upload the <code>*.quori.json</code> output from{" "}
          <code>map_to_quori.py</code>, not <code>quori_mapping.json</code>.
        </div>
        <input
          type="file"
          accept="application/json,.json"
          onChange={handleMappingFile}
          style={{ display: "block", marginTop: 6 }}
        />
        {mappingStatus && <div>{mappingStatus}</div>}
      </label>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={w}
        onChange={(e) => setW(Number(e.target.value))}
        style={{ position: "fixed", bottom: 20, left: 20, zIndex: 10 }}
      />
    </div>
  );
}

export function FaceApp() {
  return (
    <VizijRuntimeProvider assetBundle={assetBundle} autostart>
      <VizijRuntimeHud />
      <FaceRuntime />
    </VizijRuntimeProvider>
  );
}
