import { View, Text, StyleSheet } from "react-native";
import Slider from "@react-native-community/slider";
import type { EnergyCheckinRequest } from "@/lib/types";

interface EnergySliderProps {
  values: EnergyCheckinRequest;
  onChange: (values: EnergyCheckinRequest) => void;
}

const SLIDER_CONFIG: { key: keyof EnergyCheckinRequest; label: string; emoji: string }[] = [
  { key: "sleep_quality", label: "Sleep", emoji: "😴" },
  { key: "mood", label: "Mood", emoji: "😊" },
  { key: "energy_level", label: "Energy", emoji: "⚡" },
];

function LabeledSlider({
  label,
  emoji,
  value,
  onChange,
}: {
  label: string;
  emoji: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <View style={styles.row}>
      <View style={styles.labelRow}>
        <Text style={styles.emoji}>{emoji}</Text>
        <Text style={styles.label}>{label}</Text>
        <Text style={styles.value}>{value}</Text>
      </View>
      <Slider
        style={styles.slider}
        minimumValue={1}
        maximumValue={5}
        step={1}
        value={value}
        onValueChange={onChange}
        minimumTrackTintColor="#6366f1"
        maximumTrackTintColor="#1e293b"
        thumbTintColor="#a5b4fc"
      />
      <View style={styles.rangeRow}>
        <Text style={styles.rangeLabel}>1 — Poor</Text>
        <Text style={styles.rangeLabel}>5 — Excellent</Text>
      </View>
    </View>
  );
}

export function EnergySliders({ values, onChange }: EnergySliderProps) {
  return (
    <View style={styles.container}>
      {SLIDER_CONFIG.map(({ key, label, emoji }) => (
        <LabeledSlider
          key={key}
          label={label}
          emoji={emoji}
          value={(values[key] as number) ?? 3}
          onChange={(v) => onChange({ ...values, [key]: v })}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: "100%",
    gap: 20,
    paddingHorizontal: 24,
  },
  row: {
    gap: 6,
  },
  labelRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  emoji: {
    fontSize: 18,
  },
  label: {
    flex: 1,
    fontSize: 15,
    color: "#cbd5e1",
    fontWeight: "500",
  },
  value: {
    fontSize: 18,
    fontWeight: "700",
    color: "#a5b4fc",
    width: 24,
    textAlign: "right",
  },
  slider: {
    width: "100%",
    height: 40,
  },
  rangeRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  rangeLabel: {
    fontSize: 10,
    color: "#475569",
  },
});
