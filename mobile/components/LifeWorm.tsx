import { useState, useEffect, useCallback } from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import Svg, { Circle } from "react-native-svg";

const CX = 120;
const CY = 120;
const RADIUS = 100;
const STROKE_WIDTH = 8;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

interface LifeWormProps {
  durationMinutes?: number;
  onComplete?: () => void;
}

export function LifeWorm({ durationMinutes = 25, onComplete }: LifeWormProps) {
  const totalSeconds = Math.round(durationMinutes * 60);
  const [elapsed, setElapsed] = useState(0);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      setElapsed((e) => {
        if (e + 1 >= totalSeconds) {
          setRunning(false);
          onComplete?.();
          return totalSeconds;
        }
        return e + 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [running, totalSeconds, onComplete]);

  const progress = totalSeconds > 0 ? elapsed / totalSeconds : 0;
  const dashOffset = CIRCUMFERENCE * (1 - progress);

  // Worm head position — clockwise from top (-π/2)
  const angle = -Math.PI / 2 + progress * 2 * Math.PI;
  const headX = CX + RADIUS * Math.cos(angle);
  const headY = CY + RADIUS * Math.sin(angle);

  const reset = useCallback(() => {
    setRunning(false);
    setElapsed(0);
  }, []);

  return (
    <View style={styles.container}>
      <Svg width={240} height={240}>
        {/* Track ring */}
        <Circle
          cx={CX}
          cy={CY}
          r={RADIUS}
          stroke="#1e293b"
          strokeWidth={STROKE_WIDTH}
          fill="none"
        />
        {/* Progress arc */}
        <Circle
          cx={CX}
          cy={CY}
          r={RADIUS}
          stroke="#6366f1"
          strokeWidth={STROKE_WIDTH}
          fill="none"
          strokeDasharray={`${CIRCUMFERENCE} ${CIRCUMFERENCE}`}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          rotation="-90"
          origin={`${CX}, ${CY}`}
        />
        {/* Worm head */}
        {elapsed > 0 && (
          <Circle cx={headX} cy={headY} r={7} fill="#a5b4fc" />
        )}
      </Svg>

      <Text style={styles.time}>{formatTime(elapsed)}</Text>
      <Text style={styles.remaining}>{formatTime(totalSeconds - elapsed)} left</Text>

      <View style={styles.controls}>
        {!running ? (
          <TouchableOpacity style={styles.btnPrimary} onPress={() => setRunning(true)}>
            <Text style={styles.btnText}>{elapsed === 0 ? "Start" : "Resume"}</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity style={styles.btnSecondary} onPress={() => setRunning(false)}>
            <Text style={styles.btnText}>Pause</Text>
          </TouchableOpacity>
        )}
        {elapsed > 0 && (
          <TouchableOpacity style={styles.btnGhost} onPress={reset}>
            <Text style={styles.btnGhostText}>Reset</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    paddingVertical: 24,
  },
  time: {
    fontSize: 48,
    fontWeight: "700",
    color: "#e2e8f0",
    marginTop: 16,
    letterSpacing: 2,
  },
  remaining: {
    fontSize: 14,
    color: "#64748b",
    marginTop: 4,
  },
  controls: {
    flexDirection: "row",
    gap: 12,
    marginTop: 24,
    alignItems: "center",
  },
  btnPrimary: {
    backgroundColor: "#6366f1",
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 40,
  },
  btnSecondary: {
    backgroundColor: "#334155",
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 40,
  },
  btnGhost: {
    paddingVertical: 14,
    paddingHorizontal: 20,
  },
  btnText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "600",
  },
  btnGhostText: {
    color: "#64748b",
    fontSize: 14,
  },
});
