import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { useAuth } from "../../lib/auth";
import { api } from "../../lib/api";
import type { Habit } from "../../lib/types";

function streakEmoji(streak: number): string {
  if (streak >= 7) return "🔥";
  if (streak >= 3) return "⚡";
  return "◉";
}

function categoryColor(category: string | null): string {
  const colors: Record<string, string> = {
    health: "#22c55e",
    learning: "#6366f1",
    mindfulness: "#a78bfa",
    productivity: "#f59e0b",
    social: "#ec4899",
  };
  return colors[category ?? ""] ?? "#64748b";
}

export default function HabitsScreen() {
  const { token } = useAuth();
  const [habits, setHabits] = useState<Habit[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [checkinLoading, setCheckinLoading] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      const data = await api.habits.list(token);
      setHabits(data);
    } catch {
      // show empty
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  async function handleCheckin(habit: Habit) {
    if (!token || habit.checked_today || checkinLoading) return;
    setCheckinLoading(habit.id);
    try {
      const result = await api.habits.checkin(habit.id, token);
      setHabits((prev) =>
        prev.map((h) =>
          h.id === habit.id
            ? { ...h, checked_today: true, streak: result.streak }
            : h
        )
      );
    } catch {
      // ignore
    } finally {
      setCheckinLoading(null);
    }
  }

  const doneCount = habits.filter((h) => h.checked_today).length;

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
        <Text style={styles.title}>🔁 Привычки</Text>
        <Text style={styles.subtitle}>
          {doneCount}/{habits.length} сегодня
        </Text>
      </View>

      {/* Progress bar */}
      {habits.length > 0 && (
        <View style={styles.progressBar}>
          <View
            style={[
              styles.progressFill,
              { width: `${(doneCount / habits.length) * 100}%` },
            ]}
          />
        </View>
      )}

      <FlatList
        data={habits}
        keyExtractor={(h) => h.id}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); load(); }}
            tintColor="#6366f1"
          />
        }
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <Text style={styles.empty}>Нет привычек. Добавь в веб-приложении.</Text>
        }
        renderItem={({ item: habit }) => (
          <TouchableOpacity
            style={[styles.card, habit.checked_today && styles.cardDone]}
            onPress={() => handleCheckin(habit)}
            activeOpacity={0.8}
            disabled={habit.checked_today || checkinLoading === habit.id}
          >
            <View style={styles.cardLeft}>
              {/* Category dot */}
              <View
                style={[
                  styles.dot,
                  { backgroundColor: categoryColor(habit.category) },
                ]}
              />
              <View style={styles.cardText}>
                <Text
                  style={[
                    styles.habitTitle,
                    habit.checked_today && styles.habitTitleDone,
                  ]}
                >
                  {habit.title}
                </Text>
                <Text style={styles.habitMeta}>
                  {habit.target_time ?? ""}{habit.target_time ? " · " : ""}
                  {habit.estimated_minutes} мин
                </Text>
              </View>
            </View>

            <View style={styles.cardRight}>
              {checkinLoading === habit.id ? (
                <ActivityIndicator size="small" color="#6366f1" />
              ) : (
                <>
                  <Text style={styles.streakText}>
                    {streakEmoji(habit.streak)} {habit.streak}
                  </Text>
                  <View
                    style={[
                      styles.checkBox,
                      habit.checked_today && styles.checkBoxDone,
                    ]}
                  >
                    {habit.checked_today && (
                      <Text style={styles.checkMark}>✓</Text>
                    )}
                  </View>
                </>
              )}
            </View>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#0f172a" },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 56,
    paddingBottom: 12,
  },
  title: { fontSize: 22, fontWeight: "700", color: "#f1f5f9" },
  subtitle: { fontSize: 13, color: "#64748b" },
  progressBar: {
    height: 3,
    backgroundColor: "#1e293b",
    marginHorizontal: 16,
    borderRadius: 2,
    marginBottom: 12,
  },
  progressFill: {
    height: "100%",
    backgroundColor: "#6366f1",
    borderRadius: 2,
  },
  list: { paddingHorizontal: 16, paddingBottom: 24 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#1e293b",
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: "#334155",
  },
  cardDone: { borderColor: "#1e3a2f", backgroundColor: "#0f2820" },
  cardLeft: { flexDirection: "row", alignItems: "center", flex: 1 },
  dot: { width: 10, height: 10, borderRadius: 5, marginRight: 12 },
  cardText: { flex: 1 },
  habitTitle: { fontSize: 15, fontWeight: "600", color: "#f1f5f9" },
  habitTitleDone: { color: "#4b7a5e", textDecorationLine: "line-through" },
  habitMeta: { fontSize: 12, color: "#64748b", marginTop: 2 },
  cardRight: { flexDirection: "row", alignItems: "center", gap: 12 },
  streakText: { fontSize: 13, color: "#94a3b8" },
  checkBox: {
    width: 24,
    height: 24,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: "#334155",
    alignItems: "center",
    justifyContent: "center",
  },
  checkBoxDone: { backgroundColor: "#16a34a", borderColor: "#16a34a" },
  checkMark: { color: "#fff", fontSize: 13, fontWeight: "700" },
  empty: { color: "#64748b", textAlign: "center", marginTop: 40, fontSize: 14 },
});
