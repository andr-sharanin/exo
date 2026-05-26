// TDD RED — written before implementation
import { getStoredToken, storeTokens, clearTokens, isTokenExpired } from "../lib/auth";

const store: Record<string, string> = {};

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async (key: string) => store[key] ?? null),
  setItemAsync: jest.fn(async (key: string, value: string) => {
    store[key] = value;
  }),
  deleteItemAsync: jest.fn(async (key: string) => {
    delete store[key];
  }),
}));

beforeEach(() => {
  Object.keys(store).forEach((k) => delete store[k]);
});

test("getStoredToken returns null when nothing stored", async () => {
  expect(await getStoredToken()).toBeNull();
});

test("storeTokens persists access token", async () => {
  await storeTokens("access-abc", "refresh-xyz", 900);
  expect(await getStoredToken()).toBe("access-abc");
});

test("clearTokens removes access token", async () => {
  await storeTokens("access-abc", "refresh-xyz", 900);
  await clearTokens();
  expect(await getStoredToken()).toBeNull();
});

test("isTokenExpired returns true when nothing stored", async () => {
  expect(await isTokenExpired()).toBe(true);
});

test("isTokenExpired returns false for token with future expiry", async () => {
  await storeTokens("tok", "ref", 3600); // expires in 1 hour
  expect(await isTokenExpired()).toBe(false);
});

test("isTokenExpired returns true for already-expired token", async () => {
  await storeTokens("tok", "ref", -10); // expired 10 seconds ago
  expect(await isTokenExpired()).toBe(true);
});

test("clearTokens is idempotent on empty store", async () => {
  await expect(clearTokens()).resolves.not.toThrow();
});
