import { View, Text, ScrollView, StyleSheet } from "react-native";
import type { DayPlan, PlanItem } from "@/lib/types";

const STEP_TYPE_COLOR: Record<string, string> = {
  rescue_entry_step: "#ef4444",
  focus_step: "#6366f1",
  background_step: "#22c55e",
};

function PlanItemRow({ item, index }: { item: PlanItem; index: number }) {
  const accentColor = STEP_TYPE_COLOR[item.step_type] ?? "#64748b";
  return (
    <View style={styles.row}>
      <View style={[styles.accent, { backgroundColor: accentColor }]} />
      <View style={styles.indexBox}>
        <Text style={styles.indexText}>{index + 1}</Text>
      </View>
      <View style={styles.content}>
        <Text style={styles.title} numberOfLines={2}>
          {item.title}
        </Text>
        <Text style={styles.meta}>
          {item.estimated_minutes} min
          {item.step_type ? ` · ${item.step_type.replace(/_/g, " ")}` : ""}
        </Text>
      </View>
    </View>
  );
}

export function PlanList({ plan }: { plan: DayPlan }) {
  return (
    <ScrollView contentContainerStyle={styles.list}>
      <View style={styles.header}>
        <Text style={styles.date}>{plan.plan_date}</Text>
        <Text style={styles.total}>{plan.total_estimated_minutes} min total</Text>
      </View>
      {plan.items.length === 0 ? (
        <Text style={styles.empty}>No steps scheduled.</Text>
      ) : (
        plan.items.map((item, i) => (
          <PlanItemRow key={item.step_id} item={item} index={i} />
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  list: {
    paddingBottom: 32,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#1e293b",
    marginBottom: 8,
  },
  date: {
    fontSize: 14,
    color: "#94a3b8",
    fontWeight: "600",
  },
  total: {
    fontSize: 13,
    color: "#475569",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: "#0f172a",
  },
  accent: {
    width: 3,
    height: "100%",
    borderRadius: 2,
    marginRight: 12,
    alignSelf: "stretch",
  },
  indexBox: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: "#1e293b",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  indexText: {
    fontSize: 12,
    color: "#94a3b8",
    fontWeight: "600",
  },
  content: {
    flex: 1,
  },
  title: {
    fontSize: 15,
    color: "#e2e8f0",
    fontWeight: "500",
    lineHeight: 21,
  },
  meta: {
    fontSize: 12,
    color: "#64748b",
    marginTop: 3,
  },
  empty: {
    textAlign: "center",
    color: "#475569",
    marginTop: 40,
    fontSize: 14,
  },
});
