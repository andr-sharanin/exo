import NextAuth from "next-auth";
import Keycloak from "next-auth/providers/keycloak";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Keycloak({
      clientId: process.env.KEYCLOAK_CLIENT_ID!,
      clientSecret: process.env.KEYCLOAK_CLIENT_SECRET!,
      issuer: process.env.KEYCLOAK_ISSUER!,
    }),
  ],
  callbacks: {
    jwt({ token, account, profile }) {
      if (account) {
        token.accessToken = account.access_token;
        token.idToken = account.id_token;
        token.expiresAt = account.expires_at;
        // Read roles from ID token (userinfo endpoint excludes roles per mapper config)
        if (account.id_token) {
          try {
            const payload = JSON.parse(atob(account.id_token.split(".")[1]));
            const flatRoles = payload["roles"] as string[] | undefined;
            const realmAccess = payload["realm_access"] as { roles?: string[] } | undefined;
            token.roles = flatRoles ?? realmAccess?.roles ?? [];
          } catch {
            token.roles = [];
          }
        }
      }
      // Fallback: profile from userinfo if available
      if (!token.roles && profile) {
        const p = profile as Record<string, unknown>;
        const flatRoles = p["roles"] as string[] | undefined;
        const realmAccess = p["realm_access"] as { roles?: string[] } | undefined;
        token.roles = flatRoles ?? realmAccess?.roles ?? [];
      }
      return token;
    },
    session({ session, token }) {
      session.accessToken = token.accessToken as string;
      session.roles = (token.roles as string[]) ?? [];
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
});

// Augment NextAuth types
declare module "next-auth" {
  interface Session {
    accessToken: string;
    roles: string[];
  }
}
