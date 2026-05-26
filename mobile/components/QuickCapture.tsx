import { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet } from "react-native";

interface QuickCaptureProps {
  onSubmit: (text: string) => Promise<void>;
  success: boolean;
}

export function QuickCapture({ onSubmit, success }: QuickCaptureProps) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    const trimmed = text.trim();
    if (!trimmed) return;
    setSubmitting(true);
    try {
      await onSubmit(trimmed);
      setText("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Quick Capture</Text>
      <Text style={styles.subtitle}>What's on your mind?</Text>

      <TextInput
        style={styles.input}
        value={text}
        onChangeText={setText}
        placeholder="Task, idea, thought…"
        placeholderTextColor="#475569"
        multiline
        numberOfLines={4}
        textAlignVertical="top"
        autoFocus
      />

      {success && (
        <View style={styles.successBanner}>
          <Text style={styles.successText}>✓ Captured!</Text>
        </View>
      )}

      <TouchableOpacity
        style={[styles.btn, (submitting || !text.trim()) && styles.btnDisabled]}
        onPress={handleSubmit}
        disabled={submitting || !text.trim()}
        accessibilityRole="button"
        accessibilityLabel="Capture"
      >
        <Text style={styles.btnText}>{submitting ? "Capturing…" : "Capture"}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
  },
  header: {
    fontSize: 24,
    fontWeight: "700",
    color: "#e2e8f0",
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 14,
    color: "#64748b",
    marginBottom: 24,
  },
  input: {
    backgroundColor: "#1e293b",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#334155",
    color: "#e2e8f0",
    fontSize: 16,
    padding: 16,
    minHeight: 120,
    marginBottom: 16,
  },
  successBanner: {
    backgroundColor: "#14532d",
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 16,
    marginBottom: 16,
    alignItems: "center",
  },
  successText: {
    color: "#86efac",
    fontSize: 14,
    fontWeight: "600",
  },
  btn: {
    backgroundColor: "#6366f1",
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: "center",
  },
  btnDisabled: {
    opacity: 0.4,
  },
  btnText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "600",
  },
});
