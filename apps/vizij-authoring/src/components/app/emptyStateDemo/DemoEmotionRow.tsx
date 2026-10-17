import { useCallback, useEffect, useMemo, useRef } from "react";
import {
  EMOTION_POSE_KEYS,
  buildPoseWeightPathMap,
  resolvePoseSemantics,
  useVizijRuntime,
} from "@vizij/runtime-react";
import { Button } from "../../ui";

const DEFAULT_POSE_WEIGHT = 0.75;
const RELEASE_DELAY_MS = 650;

type EmotionBinding = {
  poseId: string;
  label: string;
  weightPath: string;
  semanticKey: string;
};

type CompositeEmotion = {
  label: string;
  semanticKey: string;
  parts: readonly {
    binding: EmotionBinding;
    weight: number;
  }[];
};

function formatLabel(key: string): string {
  return key
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function DemoEmotionRow({
  initialEmotion,
}: {
  initialEmotion?: string;
}) {
  const { ready, animateValue, faceId, assetBundle } = useVizijRuntime();
  const poseConfig = assetBundle.pose?.config ?? null;
  const timeoutsRef = useRef<Map<string, number>>(new Map());
  const initialEmotionAppliedRef = useRef(false);

  const bindings = useMemo((): EmotionBinding[] => {
    if (!poseConfig) {
      return [];
    }
    const weightPaths = buildPoseWeightPathMap(
      poseConfig.poses,
      poseConfig.faceId ?? faceId ?? "face",
    );
    const candidates: EmotionBinding[] = [];
    for (const pose of poseConfig.poses) {
      const semantics = resolvePoseSemantics(pose, poseConfig.poseGroups);
      if (
        semantics.kind !== "emotion" ||
        !semantics.key ||
        semantics.key === "neutral"
      ) {
        continue;
      }
      const weightPath = weightPaths.get(pose.id);
      if (!weightPath) {
        continue;
      }
      candidates.push({
        poseId: pose.id,
        label: formatLabel(semantics.key),
        weightPath,
        semanticKey: semantics.key,
      });
    }
    const orderedKeys: readonly string[] = EMOTION_POSE_KEYS.filter(
      (key) => key !== "neutral",
    );
    const byKey = new Map(
      candidates.map((binding) => [binding.semanticKey, binding] as const),
    );
    const ordered = orderedKeys
      .map((key) => byKey.get(key))
      .filter((binding): binding is EmotionBinding => Boolean(binding));
    const extras = candidates.filter(
      (binding) => !orderedKeys.includes(binding.semanticKey),
    );
    return [...ordered, ...extras];
  }, [faceId, poseConfig]);

  const compositeEmotion = useMemo<CompositeEmotion | null>(() => {
    const byKey = new Map(
      bindings.map((binding) => [binding.semanticKey, binding] as const),
    );
    const parts = [
      { key: "happy", weight: 0.6 },
      { key: "surprise", weight: 0.28 },
      { key: "concerned", weight: 0.12 },
    ]
      .map(({ key, weight }) => {
        const binding = byKey.get(key);
        return binding ? { binding, weight } : null;
      })
      .filter(
        (
          part,
        ): part is {
          binding: EmotionBinding;
          weight: number;
        } => Boolean(part),
      );
    return parts.length >= 2
      ? { label: "Curious Grin", semanticKey: "curious-grin", parts }
      : null;
  }, [bindings]);

  const trigger = useCallback(
    (binding: EmotionBinding) => {
      void animateValue(
        binding.weightPath,
        { float: DEFAULT_POSE_WEIGHT },
        { duration: 0.25 },
      );
      const existing = timeoutsRef.current.get(binding.poseId);
      if (existing) {
        window.clearTimeout(existing);
      }
      const timeout = window.setTimeout(() => {
        void animateValue(binding.weightPath, { float: 0 }, { duration: 0.35 });
        timeoutsRef.current.delete(binding.poseId);
      }, RELEASE_DELAY_MS);
      timeoutsRef.current.set(binding.poseId, timeout);
    },
    [animateValue],
  );

  const triggerComposite = useCallback(
    (emotion: CompositeEmotion) => {
      emotion.parts.forEach(({ binding, weight }) => {
        void animateValue(
          binding.weightPath,
          { float: weight },
          { duration: 0.25 },
        );
        const existing = timeoutsRef.current.get(binding.poseId);
        if (existing) {
          window.clearTimeout(existing);
        }
        const timeout = window.setTimeout(() => {
          void animateValue(
            binding.weightPath,
            { float: 0 },
            { duration: 0.35 },
          );
          timeoutsRef.current.delete(binding.poseId);
        }, RELEASE_DELAY_MS);
        timeoutsRef.current.set(binding.poseId, timeout);
      });
    },
    [animateValue],
  );

  useEffect(() => {
    if (
      !initialEmotion ||
      !ready ||
      initialEmotionAppliedRef.current ||
      bindings.length === 0
    ) {
      return;
    }
    if (initialEmotion === compositeEmotion?.semanticKey) {
      compositeEmotion.parts.forEach(({ binding, weight }) => {
        void animateValue(
          binding.weightPath,
          { float: weight },
          { duration: 0.25 },
        );
      });
      initialEmotionAppliedRef.current = true;
      return;
    }
    const binding = bindings.find(
      (candidate) => candidate.semanticKey === initialEmotion,
    );
    if (!binding) {
      return;
    }
    void animateValue(
      binding.weightPath,
      { float: DEFAULT_POSE_WEIGHT },
      { duration: 0.25 },
    );
    initialEmotionAppliedRef.current = true;
  }, [animateValue, bindings, compositeEmotion, initialEmotion, ready]);

  useEffect(() => {
    const timeouts = timeoutsRef.current;
    return () => {
      timeouts.forEach((id) => window.clearTimeout(id));
      timeouts.clear();
    };
  }, []);

  if (!ready || bindings.length === 0) {
    return null;
  }

  return (
    <div
      data-testid="empty-state-demo-emotions"
      className="flex flex-wrap justify-center gap-2"
    >
      {bindings.map((binding) => (
        <Button
          key={binding.poseId}
          data-testid={`empty-state-demo-emotion-${binding.semanticKey}`}
          variant="secondary"
          size="sm"
          onClick={() => trigger(binding)}
        >
          {binding.label}
        </Button>
      ))}
      {compositeEmotion ? (
        <Button
          data-testid="empty-state-demo-emotion-curious-grin"
          variant="secondary"
          size="sm"
          onClick={() => triggerComposite(compositeEmotion)}
          title="Blend happy, surprise, and concern into a slightly stranger expression"
        >
          {compositeEmotion.label}
        </Button>
      ) : null}
    </div>
  );
}
