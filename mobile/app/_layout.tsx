import { useEffect, useState } from "react";
import { Stack, useRouter } from "expo-router";
import { getStoredToken, isTokenExpired } from "@/lib/auth";
import { registerForPushNotifications } from "@/lib/notifications";
import { api } from "@/lib/api";

export default function RootLayout() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    (async () => {
      const token = await getStoredToken();
      const expired = await isTokenExpired();
      if (!token || expired) {
        router.replace("/login");
      } else {
        // Register push notifications in background (best effort)
        registerForPushNotifications()
          .then((pushToken) => {
            if (pushToken && token) {
              api.push.subscribe({ endpoint: "expo", token: pushToken }, token).catch(() => {});
            }
          })
          .catch(() => {});
      }
      setChecked(true);
    })();
  }, []);

  if (!checked) return null;

  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: "#0f172a" } }}>
      <Stack.Screen name="(tabs)" />
      <Stack.Screen name="login" options={{ gestureEnabled: false }} />
    </Stack>
  );
}
