import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  TextInput,
} from "react-native";
import { useAuth } from "../../lib/auth";
import { api } from "../../lib/api";
import type { Command } from "../../lib/types";

const STATUS_COLORS: Record<string, string> = {
  pending_confirmation: "#f59e0b",
  pending_analysis:    "#6366f1",
  confirmed:           "#22c55e",
  deferred:            "#ef4444",
};

const STATUS_LABELS: Record<string, string> = {
  pending_confirmation: "Ждёт решения",
  pending_analysis:     "Анализируется",
  confirmed:            "Подтверждено",
  deferred:             "Отложено",
};

export default function InboxScreen() {
  const { token } = useAuth();
  const [commands, setCommands] = useState<Command[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [captureText, setCaptureText] = useState("");
  const [capturing, setCapturing] = useState(false);
  const [confirming, setConfirming] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      const data = await api.commands.list(token, 30);
      setCommands(data);
    } catch {
      // show empty
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  async function handleCapture() {
    if (!token || !captureText.trim()) return;
    setCapturing(true);
    try {
      const cmd = await api.commands.create(
        {
          raw_payload_ref: captureText.trim(),
          ingress_channel: "mobile",
          ingress_modality: "text",
          idempotency_key: `mob-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        },
        token
      );
      setCommands((prev) => [cmd, ...prev]);
      setCaptureText("");
    } catch {
      // ignore
    } finally {
      setCapturing(false);
    }
  }

  async function handleDecision(commandId: string, decision: "confirmed" | "deferred") {
    if (!token) return;
    setConfirming(commandId);
    try {
      await api.commands.confirm(commandId, decision, undefined, token);
      setCommands((prev) =>
        prev.map((c) =>
          c.id === commandId
            ? { ...c, kernel_status: decision }
            : c
        )
      );
    } catch {
      // ignore
    } finally {
      setConfirming(null);
    }
  }

  const pendingCount = commands.filter(
    (c) => c.kernel_status === "pending_confirmation"
  ).length;

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color="#6366f1" size="large" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>
          📥 Inbox{pendingCount > 0 ? ` (${pendingCount})` : ""}
        </Text>
      </View>

      {/* Quick capture */}
      <View style={styles.captureRow}>
        <TextInput
          style={styles.captureInput}
          value={captureText}
          onChangeText={setCaptureText}
          placeholder="Быстрый захват задачи..."
          placeholderTextColor="#475569"
          returnKeyType="send"
          onSubmitEditing={handleCapture}
        />
        <TouchableOpacity
          style={[styles.captureBtn, (!captureText.trim() || capturing) && styles.captureBtnDis]}
          onPress={handleCapture}
          disabled={!captureText.trim() || capturing}
        >
          {capturing ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.captureBtnText}>→</Text>
          )}
        </TouchableOpacity>
      </View>

      <FlatList
        data={commands}
        keyExtractor={(c) => c.id}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); load(); }}
            tintColor="#6366f1"
          />
        }
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <Text style={styles.empty}>Нет задач в Inbox</Text>
        }
        renderItem={({ item: cmd }) => {
          const isPending = cmd.kernel_status === "pending_confirmation";
          const statusColor = STATUS_COLORS[cmd.kernel_status ?? ""] ?? "#64748b";
          const statusLabel = STATUS_LABELS[cmd.kernel_status ?? ""] ?? cmd.kernel_status ?? "—";

          return (
            <View style={[styles.card, isPending && styles.cardPending]}>
              <View style={styles.cardTop}>
                <Text style={styles.cmdText} numberOfLines={2}>
                  {cmd.raw_input ?? "—"}
                </Text>
                <View style={[styles.statusPill, { backgroundColor: `${statusColor}33` }]}>
                  <Text style={[styles.statusText, { color: statusColor }]}>
                    {statusLabel}
                  </Text>
                </View>
              </View>

              <Text style={styles.cardMeta}>
                {cmd.ingress_channel} · {new Date(cmd.submitted_at).toLocaleString("ru-RU", {
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </Text>

              {isPending && (
                <View style={styles.actionRow}>
                  <TouchableOpacity
                    style={styles.btnConfirm}
                    onPress={() => handleDecision(cmd.id, "confirmed")}
                    disabled={confirming === cmd.id}
                  >
                    {confirming === cmd.id ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : (
                      <Text style={styles.btnText}>✓ Подтвердить</Text>
                    )}
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.btnDefer}
                    onPress={() => handleDecision(cmd.id, "deferred")}
                    disabled={confirming === cmd.id}
                  >
                    <Text style={[styles.btnText, { color: "#94a3b8" }]}>
                      Отложить
                    </Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#0f172a" },
  header: {
    paddingHorizontal: 16,
    paddingTop: 56,
    paddingBottom: 8,
  },
  title: { fontSize: 22, fontWeight: "700", color: "#f1f5f9" },
  captureRow: {
    flexDirection: "row",
    gap: 8,
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  captureInput: {
    flex: 1,
    backgroundColor: "#1e293b",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 14,
    color: "#f1f5f9",
    borderWidth: 1,
    borderColor: "#334155",
  },
  captureBtn: {
    backgroundColor: "#6366f1",
    borderRadius: 10,
    paddingHorizontal: 16,
    alignItems: "center",
    justifyContent: "center",
  },
  captureBtnDis: { opacity: 0.5 },
  captureBtnText: { color: "#fff", fontSize: 18, fontWeight: "700" },
  list: { paddingHorizontal: 16, paddingBottom: 24 },
  card: {
    backgroundColor: "#1e293b",
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: "#334155",
  },
  cardPending: { borderColor: "#78350f" },
  cardTop: { flexDirection: "row", alignItems: "flex-start", gap: 8, marginBottom: 6 },
  cmdText: { flex: 1, fontSize: 14, color: "#f1f5f9", lineHeight: 20 },
  statusPill: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3 },
  statusText: { fontSize: 11, fontWeight: "600" },
  cardMeta: { fontSize: 11, color: "#475569", marginBottom: 10 },
  actionRow: { flexDirection: "row", gap: 10 },
  btnConfirm: {
    flex: 1,
    backgroundColor: "#1d4ed8",
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: "center",
  },
  btnDefer: {
    flex: 1,
    backgroundColor: "#1e293b",
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#334155",
  },
  btnText: { color: "#fff", fontSize: 13, fontWeight: "600" },
  empty: { color: "#64748b", textAlign: "center", marginTop: 40, fontSize: 14 },
});
