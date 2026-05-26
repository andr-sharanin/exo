import { useEffect, useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from "react-native";
import {
  useAuthRequest,
  makeRedirectUri,
  ResponseType,
} from "expo-auth-session";
import * as WebBrowser from "expo-web-browser";
import Constants from "expo-constants";
import { useRouter } from "expo-router";
import { storeTokens } from "@/lib/auth";

WebBrowser.maybeCompleteAuthSession();

const KEYCLOAK_URL: string =
  (Constants.expoConfig?.extra?.keycloakUrl as string | undefined) ?? "http://10.0.2.2:8080";
const REALM = "exocortex";
const CLIENT_ID = "exocortex-mobile";

const discovery = {
  authorizationEndpoint: `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/auth`,
  tokenEndpoint: `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token`,
  revocationEndpoint: `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/revoke`,
};

export default function LoginScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const redirectUri = makeRedirectUri({ scheme: "exocortex", path: "auth" });

  const [request, response, promptAsync] = useAuthRequest(
    {
      clientId: CLIENT_ID,
      scopes: ["openid", "profile", "email"],
      redirectUri,
      usePKCE: true,
    },
    discovery,
  );

  useEffect(() => {
    if (response?.type !== "success") return;
    const { code } = response.params;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const tokenRes = await fetch(discovery.tokenEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({
            client_id: CLIENT_ID,
            code,
            redirect_uri: redirectUri,
            grant_type: "authorization_code",
            code_verifier: request!.codeVerifier!,
          }).toString(),
        });

        if (!tokenRes.ok) {
          throw new Error(`Token exchange failed: ${tokenRes.status}`);
        }

        const tokens = (await tokenRes.json()) as {
          access_token: string;
          refresh_token: string;
          expires_in: number;
        };

        await storeTokens(tokens.access_token, tokens.refresh_token, tokens.expires_in);
        router.replace("/(tabs)/worm");
      } catch (e) {
        setError("Login failed. Check your connection and try again.");
      } finally {
        setLoading(false);
      }
    })();
  }, [response]);

  return (
    <View style={styles.container}>
      <View style={styles.logo}>
        <Text style={styles.logoText}>⬡</Text>
      </View>

      <Text style={styles.title}>ExoCortex</Text>
      <Text style={styles.subtitle}>Cognitive OS for high-agency humans</Text>

      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}

      {loading ? (
        <ActivityIndicator color="#6366f1" size="large" style={styles.loader} />
      ) : (
        <TouchableOpacity
          style={[styles.btn, !request && styles.btnDisabled]}
          disabled={!request}
          onPress={() => promptAsync()}
        >
          <Text style={styles.btnText}>Sign in with Keycloak</Text>
        </TouchableOpacity>
      )}

      <Text style={styles.hint}>
        First time? Register at your ExoCortex instance and ask an admin to assign your role.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
    alignItems: "center",
    justifyContent: "center",
    padding: 32,
  },
  logo: {
    marginBottom: 24,
  },
  logoText: {
    fontSize: 64,
    color: "#6366f1",
  },
  title: {
    fontSize: 34,
    fontWeight: "800",
    color: "#e2e8f0",
    letterSpacing: 1,
  },
  subtitle: {
    fontSize: 14,
    color: "#64748b",
    marginTop: 8,
    marginBottom: 48,
    textAlign: "center",
  },
  errorBox: {
    backgroundColor: "#450a0a",
    borderRadius: 10,
    padding: 14,
    width: "100%",
    marginBottom: 20,
  },
  errorText: {
    color: "#fca5a5",
    fontSize: 13,
    textAlign: "center",
  },
  loader: {
    marginVertical: 24,
  },
  btn: {
    backgroundColor: "#6366f1",
    borderRadius: 14,
    paddingVertical: 16,
    paddingHorizontal: 48,
    width: "100%",
    alignItems: "center",
  },
  btnDisabled: {
    opacity: 0.5,
  },
  btnText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "700",
  },
  hint: {
    fontSize: 12,
    color: "#334155",
    textAlign: "center",
    marginTop: 32,
    lineHeight: 18,
  },
});
