import * as SecureStore from "expo-secure-store";

const ACCESS_TOKEN_KEY = "exocortex_access_token";
const REFRESH_TOKEN_KEY = "exocortex_refresh_token";
const TOKEN_EXPIRY_KEY = "exocortex_token_expiry";

export async function getStoredToken(): Promise<string | null> {
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}

export async function getStoredRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
}

export async function storeTokens(
  accessToken: string,
  refreshToken: string,
  expiresIn: number,
): Promise<void> {
  const expiry = Date.now() + expiresIn * 1000;
  await Promise.all([
    SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken),
    SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken),
    SecureStore.setItemAsync(TOKEN_EXPIRY_KEY, String(expiry)),
  ]);
}

export async function clearTokens(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY),
    SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY),
    SecureStore.deleteItemAsync(TOKEN_EXPIRY_KEY),
  ]);
}

export async function isTokenExpired(): Promise<boolean> {
  const expiry = await SecureStore.getItemAsync(TOKEN_EXPIRY_KEY);
  if (!expiry) return true;
  return Date.now() >= parseInt(expiry, 10);
}
