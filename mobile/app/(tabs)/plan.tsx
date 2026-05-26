import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from "react-native";
import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";
import { PlanList } from "@/components/PlanList";
import type { DayPlan } from "@/lib/types";

export default function PlanScreen() {
  const [plan, setPlan] = useState<DayPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPlan = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getStoredToken();
      if (!token) return;
      const data = await api.secretary.getTodayPlan(token);
      setPlan(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("HTTP 404")) {
        setPlan(null);
      } else {
        setError("Could not load plan. Check your connection.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadPlan(); }, [loadPlan]);

  async function generatePlan() {
    setGenerating(true);
    setError(null);
    try {
      const token = await getStoredToken();
      if (!token) return;
      await api.secretary.generatePlan(token);
      // Poll until plan appears (backend generates async)
      for (let i = 0; i < 15; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        try {
          const data = await api.secretary.getTodayPlan(token);
          setPlan(data);
          return;
        } catch {
          // not ready yet — keep polling
        }
      }
      setError("Plan generation timed out. Pull down to refresh.");
    } catch {
      setError("Failed to generate plan.");
    } finally {
      setGenerating(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color="#6366f1" size="large" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={loadPlan}>
          <Text style={styles.retryText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.titleBar}>
        <Text style={styles.header}>Today's Plan</Text>
        {plan && (
          <TouchableOpacity onPress={loadPlan}>
            <Text style={styles.refresh}>↻</Text>
          </TouchableOpacity>
        )}
      </View>

      {plan ? (
        <PlanList plan={plan} />
      ) : (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>📋</Text>
          <Text style={styles.emptyTitle}>No plan for today</Text>
          <Text style={styles.emptySubtitle}>
            Generate a plan based on your current energy and pending steps.
          </Text>
          <TouchableOpacity
            style={[styles.btn, generating && styles.btnDisabled]}
            onPress={generatePlan}
            disabled={generating}
          >
            <Text style={styles.btnText}>
              {generating ? "Generating…" : "Generate Plan"}
            </Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
    paddingTop: 60,
  },
  center: {
    flex: 1,
    backgroundColor: "#0f172a",
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
  },
  titleBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    marginBottom: 8,
  },
  header: {
    fontSize: 24,
    fontWeight: "700",
    color: "#e2e8f0",
  },
  refresh: {
    fontSize: 22,
    color: "#475569",
  },
  emptyContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 40,
    gap: 12,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 8,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#94a3b8",
  },
  emptySubtitle: {
    fontSize: 14,
    color: "#475569",
    textAlign: "center",
    lineHeight: 20,
  },
  btn: {
    marginTop: 16,
    backgroundColor: "#6366f1",
    borderRadius: 14,
    paddingVertical: 14,
    paddingHorizontal: 40,
    alignItems: "center",
  },
  btnDisabled: {
    opacity: 0.4,
  },
  btnText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "700",
  },
  errorText: {
    color: "#fca5a5",
    fontSize: 14,
    textAlign: "center",
  },
  retryBtn: {
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#334155",
  },
  retryText: {
    color: "#94a3b8",
    fontSize: 14,
  },
});
