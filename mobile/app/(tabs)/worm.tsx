import { View, Text, StyleSheet, Alert } from "react-native";
import { useEffect, useState } from "react";
import { LifeWorm } from "@/components/LifeWorm";
import { api } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";
import type { DayPlan } from "@/lib/types";

export default function WormScreen() {
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [duration, setDuration] = useState(25);

  useEffect(() => {
    (async () => {
      const token = await getStoredToken();
      if (!token) return;
      try {
        const plan = await api.secretary.getTodayPlan(token) as DayPlan;
        const first = plan.items[0];
        if (first) {
          setCurrentStep(first.title);
          setDuration(first.estimated_minutes || 25);
        }
      } catch {
        // No plan today — default 25-min Pomodoro
      }
    })();
  }, []);

  function handleComplete() {
    Alert.alert("Session Complete", "Great work! Take a short break.", [{ text: "OK" }]);
  }

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Focus Session</Text>
      {currentStep && (
        <View style={styles.stepBadge}>
          <Text style={styles.stepText} numberOfLines={2}>{currentStep}</Text>
        </View>
      )}
      <LifeWorm durationMinutes={duration} onComplete={handleComplete} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
    alignItems: "center",
    paddingTop: 60,
  },
  header: {
    fontSize: 12,
    fontWeight: "700",
    color: "#94a3b8",
    letterSpacing: 1,
    textTransform: "uppercase",
    marginBottom: 8,
  },
  stepBadge: {
    backgroundColor: "#1e293b",
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 20,
    maxWidth: 300,
    marginBottom: 8,
  },
  stepText: {
    color: "#e2e8f0",
    fontSize: 15,
    textAlign: "center",
    fontWeight: "500",
  },
});
