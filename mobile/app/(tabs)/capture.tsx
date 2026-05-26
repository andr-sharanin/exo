import { View, StyleSheet } from "react-native";
import { useState } from "react";
import { QuickCapture } from "@/components/QuickCapture";
import { api } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";

export default function CaptureScreen() {
  const [success, setSuccess] = useState(false);

  async function handleCapture(text: string) {
    const token = await getStoredToken();
    if (!token) return;
    await api.commands.create({ raw_input: text }, token);
    setSuccess(true);
    setTimeout(() => setSuccess(false), 2000);
  }

  return (
    <View style={styles.container}>
      <QuickCapture onSubmit={handleCapture} success={success} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
    paddingTop: 60,
  },
});
