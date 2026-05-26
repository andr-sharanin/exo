"use client";

import { signIn } from "next-auth/react";

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm space-y-8 p-8">
        <div className="text-center">
          <div className="text-6xl mb-4">🧠</div>
          <h1 className="text-3xl font-bold text-white">ExoCortex</h1>
          <p className="mt-2 text-gray-400 text-sm">Your external executive brain</p>
        </div>

        <button
          onClick={() => signIn("keycloak", { callbackUrl: "/dashboard" })}
          className="w-full flex items-center justify-center gap-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 px-4 transition-colors"
        >
          Continue with your account
        </button>

        <p className="text-center text-xs text-gray-600">
          Single sign-on via Keycloak
        </p>
      </div>
    </div>
  );
}
