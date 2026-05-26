"use client";

import { useState, useRef, useEffect } from "react";
import type { AgentSession, AgentMessage } from "@/lib/types";
import { api } from "@/lib/api";
import clsx from "clsx";

export function ChatWindow({ session, token }: { session: AgentSession; token: string }) {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    const userMsg: AgentMessage = {
      id: crypto.randomUUID(),
      session_id: session.id,
      role: "user",
      content: text,
      message_order: messages.length,
      model_used: null,
    };
    setMessages((m) => [...m, userMsg]);
    setLoading(true);
    try {
      const reply = await api.agents.sendMessage(session.id, text, token) as AgentMessage;
      // Parse structured response if JSON
      let displayContent = reply.content;
      try {
        const parsed = JSON.parse(reply.content);
        displayContent = parsed.response ?? reply.content;
      } catch {
        // Plain text response
      }
      setMessages((m) => [...m, { ...reply, content: displayContent }]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          session_id: session.id,
          role: "assistant",
          content: `Error: ${(err as Error).message}`,
          message_order: m.length,
          model_used: null,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <p className="text-center text-gray-600 text-sm mt-8">
            Start a conversation…
          </p>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={clsx(
              "flex",
              msg.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            <div
              className={clsx(
                "max-w-[75%] rounded-2xl px-4 py-3 text-sm",
                msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-br-sm"
                  : "bg-gray-800 text-gray-100 rounded-bl-sm"
              )}
            >
              {msg.content}
              {msg.model_used && (
                <p className="text-xs text-gray-500 mt-1 font-mono">{msg.model_used}</p>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-2xl rounded-bl-sm px-4 py-3">
              <span className="text-gray-400 text-sm">Thinking…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            placeholder="Type a message…"
            disabled={loading}
            className="flex-1 rounded-xl bg-gray-900 border border-gray-700 text-gray-100 text-sm px-4 py-3 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white px-5 font-semibold transition-colors"
          >
            →
          </button>
        </div>
      </div>
    </div>
  );
}
