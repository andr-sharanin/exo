import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";

type IoniconsName = React.ComponentProps<typeof Ionicons>["name"];

const TABS: { name: string; title: string; icon: IoniconsName; iconActive: IoniconsName }[] = [
  { name: "worm",    title: "Focus",     icon: "timer-outline",          iconActive: "timer" },
  { name: "inbox",   title: "Inbox",     icon: "mail-outline",           iconActive: "mail" },
  { name: "capture", title: "Capture",   icon: "add-circle-outline",     iconActive: "add-circle" },
  { name: "habits",  title: "Привычки",  icon: "repeat-outline",         iconActive: "repeat" },
  { name: "energy",  title: "Energy",    icon: "battery-charging-outline", iconActive: "battery-charging" },
  { name: "plan",    title: "Plan",      icon: "list-outline",           iconActive: "list" },
];

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: "#0f172a",
          borderTopColor: "#1e293b",
          borderTopWidth: 1,
          paddingBottom: 6,
          height: 60,
        },
        tabBarActiveTintColor: "#6366f1",
        tabBarInactiveTintColor: "#475569",
        tabBarLabelStyle: { fontSize: 10, fontWeight: "600" },
      }}
    >
      {TABS.map(({ name, title, icon, iconActive }) => (
        <Tabs.Screen
          key={name}
          name={name}
          options={{
            title,
            tabBarIcon: ({ color, size, focused }) => (
              <Ionicons name={focused ? iconActive : icon} size={size} color={color} />
            ),
          }}
        />
      ))}
    </Tabs>
  );
}
