import { View, Text, TouchableOpacity, StyleSheet, Alert, ScrollView } from "react-native";
import { useState } from "react";
import { EnergySliders } from "@/components/EnergySliders";
import { api } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";
import type { EnergyCheckinRequest } from "@/lib/types";

const DEFAULT_VALUES: EnergyCheckinRequest = {
  sleep_quality: 3,
  mood: 3,
  energy_level: 3,
};

function stateLabel(score: number): string {
  if (score <= 3) return "constrained";
  if (score <= 6) return "sufficient";
  return "sufficient";
}

export default function EnergyScreen() {
  const [values, setValues] = useState<EnergyCheckinRequest>(DEFAULT_VALUES);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [energyState, setEnergyState] = useState<string | null>(null);

  async function submit() {
    setSubmitting(true);
    try {
      const token = await getStoredToken();
      if (!token) {
        Alert.alert("Error", "Not authenticated. Please log in again.");
        return;
      }
      const result = await api.energy.checkin(values, token);
      setEnergyState(result.state ?? result.energy_state ?? null);
      setSubmitted(true);
    } catch {
      Alert.alert("Error", "Failed to log energy. Check your connection.");
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <View style={[styles.container, styles.successContainer]}>
        <Text style={styles.successIcon}>⚡</Text>
        <Text style={styles.successTitle}>Energy Logged</Text>
        {energyState && (
          <Text style={styles.energyState}>
            State: <Text style={styles.energyStateValue}>{energyState}</Text>
          </Text>
        )}
        <TouchableOpacity
          style={styles.againBtn}
          onPress={() => { setSubmitted(false); setValues(DEFAULT_VALUES); }}
        >
          <Text style={styles.againBtnText}>Log Again</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const avg = Math.round((values.sleep_quality + values.mood + values.energy_level) / 3);

  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.container}>
      <Text style={styles.header}>Energy Check-In</Text>
      <Text style={styles.subtitle}>Average: {avg}/5 · {stateLabel(avg)}</Text>

      <EnergySliders values={values} onChange={setValues} />

      <TouchableOpacity
        style={[styles.btn, submitting && styles.btnDisabled]}
        onPress={submit}
        disabled={submitting}
      >
        <Text style={styles.btnText}>{submitting ? "Logging…" : "Log Energy"}</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: "#0f172a" },
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
    paddingTop: 60,
    paddingBottom: 32,
    alignItems: "center",
  },
  successContainer: { justifyContent: "center", gap: 12 },
  header: {
    fontSize: 24, fontWeight: "700", color: "#e2e8f0",
    marginBottom: 6, alignSelf: "flex-start", paddingHorizontal: 24,
  },
  subtitle: {
    fontSize: 13, color: "#64748b", marginBottom: 32,
    alignSelf: "flex-start", paddingHorizontal: 24,
  },
  btn: {
    backgroundColor: "#6366f1", borderRadius: 14, paddingVertical: 16,
    marginHorizontal: 24, marginTop: 40, alignItems: "center", width: "89%",
  },
  btnDisabled: { opacity: 0.4 },
  btnText: { color: "#ffffff", fontSize: 16, fontWeight: "700" },
  successIcon: { fontSize: 64, textAlign: "center" },
  successTitle: { fontSize: 24, fontWeight: "700", color: "#e2e8f0", textAlign: "center" },
  energyState: { fontSize: 15, color: "#94a3b8", textAlign: "center" },
  energyStateValue: { color: "#a5b4fc", fontWeight: "600", textTransform: "capitalize" },
  againBtn: {
    marginTop: 24, paddingVertical: 12, paddingHorizontal: 32,
    borderRadius: 12, borderWidth: 1, borderColor: "#334155",
  },
  againBtnText: { color: "#94a3b8", fontSize: 14, fontWeight: "600" },
});
