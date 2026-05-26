"use client";

import { useState } from "react";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { AgentPersona, KnowledgeDoc } from "@/lib/types";

const TIER_LABEL: Record<number, string> = { 1: "Механический", 2: "Аналитический", 3: "Стратегический" };
const TIER_COLOR: Record<number, string> = { 1: "text-gray-400", 2: "text-blue-400", 3: "text-purple-400" };

type AgentTab = "prompt" | "train" | "knowledge" | "settings";

// ── Inline rule editor ─────────────────────────────────────────────────────────
function RulesEditor({
  rules,
  onChange,
}: {
  rules: string[];
  onChange: (r: string[]) => void;
}) {
  const [newRule, setNewRule] = useState("");
  return (
    <div className="space-y-2">
      {rules.map((r, i) => (
        <div key={i} className="flex items-start gap-2">
          <span className="text-gray-600 text-xs mt-2 flex-shrink-0">{i + 1}.</span>
          <p className="flex-1 text-sm text-gray-300 bg-gray-800 rounded-lg px-3 py-2">{r}</p>
          <button
            onClick={() => onChange(rules.filter((_, j) => j !== i))}
            className="text-gray-700 hover:text-red-400 text-xs mt-2 transition-colors"
          >
            ✕
          </button>
        </div>
      ))}
      <div className="flex gap-2">
        <input
          value={newRule}
          onChange={(e) => setNewRule(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && newRule.trim()) {
              onChange([...rules, newRule.trim()]);
              setNewRule("");
            }
          }}
          placeholder="Добавить правило поведения... (Enter)"
          className="flex-1 rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-300 px-3 py-2 focus:outline-none focus:border-indigo-500"
        />
      </div>
    </div>
  );
}

// ── Knowledge base panel ──────────────────────────────────────────────────────
function KnowledgePanel({
  entityType,
  docs,
  token,
  onUpdate,
}: {
  entityType: string;
  docs: KnowledgeDoc[];
  token: string;
  onUpdate: (docs: KnowledgeDoc[]) => void;
}) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [adding, setAdding] = useState(false);
  const [showForm, setShowForm] = useState(false);

  async function handleAdd() {
    if (!title.trim() || !content.trim()) return;
    setAdding(true);
    try {
      await api.adminAgents.addKnowledge(entityType, title.trim(), content.trim(), token);
      onUpdate([
        ...docs,
        { title: title.trim(), content: content.trim(), added_at: new Date().toISOString() },
      ]);
      setTitle("");
      setContent("");
      setShowForm(false);
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(idx: number) {
    await api.adminAgents.removeKnowledge(entityType, idx, token);
    onUpdate(docs.filter((_, i) => i !== idx));
  }

  return (
    <div className="space-y-3">
      {docs.length === 0 && !showForm ? (
        <p className="text-xs text-gray-600 text-center py-4">База знаний пуста</p>
      ) : (
        docs.map((doc, i) => (
          <div key={i} className="rounded-lg bg-gray-800 border border-gray-700 p-3">
            <div className="flex items-start justify-between gap-2 mb-1">
              <p className="text-sm font-medium text-gray-200">{doc.title}</p>
              <button
                onClick={() => handleRemove(i)}
                className="text-xs text-gray-700 hover:text-red-400 flex-shrink-0 transition-colors"
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-gray-500 leading-relaxed line-clamp-3">{doc.content}</p>
          </div>
        ))
      )}

      {showForm ? (
        <div className="rounded-lg bg-gray-800 border border-indigo-800/40 p-3 space-y-2">
          <input
            autoFocus
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Название документа"
            className="w-full rounded-lg bg-gray-700 border border-gray-600 text-sm text-gray-200 px-3 py-2 focus:outline-none focus:border-indigo-500"
          />
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Содержание документа..."
            rows={5}
            className="w-full rounded-lg bg-gray-700 border border-gray-600 text-sm text-gray-200 px-3 py-2 focus:outline-none focus:border-indigo-500 resize-none"
          />
          <div className="flex gap-2">
            <button
              onClick={handleAdd}
              disabled={adding || !title.trim() || !content.trim()}
              className="rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium px-4 py-2 transition-colors"
            >
              {adding ? "…" : "Добавить"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-400 text-xs px-4 py-2 transition-colors"
            >
              Отмена
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowForm(true)}
          className="w-full rounded-lg border border-dashed border-gray-700 hover:border-indigo-600 text-gray-600 hover:text-indigo-400 text-xs py-2.5 transition-colors"
        >
          + Добавить документ
        </button>
      )}
    </div>
  );
}

// ── Persona detail panel ──────────────────────────────────────────────────────
function PersonaDetail({
  persona: initial,
  token,
  onUpdate,
}: {
  persona: AgentPersona;
  token: string;
  onUpdate: (p: AgentPersona) => void;
}) {
  const [persona, setPersona] = useState(initial);
  const [tab, setTab] = useState<AgentTab>("prompt");
  const [systemPrompt, setSystemPrompt] = useState(persona.system_prompt ?? "");
  const [rules, setRules] = useState(persona.behavior_rules);
  const [training, setTraining] = useState("");
  const [saving, setSaving] = useState(false);
  const [training_saving, setTrainingSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function savePromptAndRules() {
    setSaving(true);
    try {
      const updated = await api.adminAgents.update(
        persona.entity_type,
        { system_prompt: systemPrompt, behavior_rules: rules },
        token
      ) as AgentPersona;
      const merged = { ...persona, ...updated };
      setPersona(merged);
      onUpdate(merged);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  async function submitTraining() {
    if (!training.trim()) return;
    setTrainingSaving(true);
    try {
      await api.adminAgents.train(persona.entity_type, training.trim(), token);
      const updated = { ...persona, training_context_length: persona.training_context_length + training.length };
      setPersona(updated);
      onUpdate(updated);
      setTraining("");
    } finally {
      setTrainingSaving(false);
    }
  }

  async function toggleEnabled() {
    if (persona.is_default) return;
    const updated = await api.adminAgents.update(
      persona.entity_type,
      { is_enabled: !persona.is_enabled },
      token
    ) as AgentPersona;
    const merged = { ...persona, ...updated };
    setPersona(merged);
    onUpdate(merged);
  }

  const TABS: { id: AgentTab; label: string }[] = [
    { id: "prompt", label: "Промпт" },
    { id: "train", label: "Обучение" },
    { id: "knowledge", label: `База знаний (${persona.knowledge_base_count})` },
    { id: "settings", label: "Настройки" },
  ];

  return (
    <div className="border-t border-gray-800 pt-4 space-y-4">
      {/* Tabs */}
      <div className="flex gap-1 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={clsx(
              "flex-shrink-0 text-xs px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap",
              tab === t.id
                ? "bg-indigo-600 text-white"
                : "bg-gray-800 text-gray-500 hover:text-gray-300"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab: Prompt */}
      {tab === "prompt" && (
        <div className="space-y-3">
          <label className="block">
            <span className="text-xs text-gray-500 font-medium">System Prompt</span>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={10}
              className="mt-1.5 w-full rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-200 px-3 py-2.5 focus:outline-none focus:border-indigo-500 resize-none font-mono"
              placeholder="You are..."
            />
          </label>

          <div>
            <span className="text-xs text-gray-500 font-medium">Правила поведения</span>
            <div className="mt-1.5">
              <RulesEditor rules={rules} onChange={setRules} />
            </div>
          </div>

          <button
            onClick={savePromptAndRules}
            disabled={saving}
            className={clsx(
              "rounded-lg text-sm font-medium px-5 py-2 transition-colors",
              saved
                ? "bg-green-700 text-white"
                : "bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white"
            )}
          >
            {saving ? "Сохраняю..." : saved ? "✓ Сохранено" : "Сохранить"}
          </button>
        </div>
      )}

      {/* Tab: Training */}
      {tab === "train" && (
        <div className="space-y-3">
          <div className="rounded-lg bg-gray-800 px-3 py-2 text-xs text-gray-500">
            Накоплено обучения: <span className="text-gray-300 font-medium">{persona.training_context_length} симв.</span>
            {persona.last_trained_at && (
              <span className="ml-2">
                · последнее: {new Date(persona.last_trained_at).toLocaleDateString("ru-RU")}
              </span>
            )}
          </div>
          <textarea
            value={training}
            onChange={(e) => setTraining(e.target.value)}
            rows={8}
            placeholder="Добавь контекст, факты, стиль общения, примеры ответов..."
            className="w-full rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-200 px-3 py-2.5 focus:outline-none focus:border-indigo-500 resize-none"
          />
          <button
            onClick={submitTraining}
            disabled={training_saving || !training.trim()}
            className="rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium px-5 py-2 transition-colors"
          >
            {training_saving ? "Добавляю..." : "Добавить к обучению"}
          </button>
        </div>
      )}

      {/* Tab: Knowledge */}
      {tab === "knowledge" && (
        <KnowledgePanel
          entityType={persona.entity_type}
          docs={persona.knowledge_base}
          token={token}
          onUpdate={(docs) => {
            const updated = { ...persona, knowledge_base: docs, knowledge_base_count: docs.length };
            setPersona(updated);
            onUpdate(updated);
          }}
        />
      )}

      {/* Tab: Settings */}
      {tab === "settings" && (
        <div className="space-y-4">
          <div className="rounded-lg bg-gray-800 p-3 space-y-2 text-xs text-gray-400">
            <div className="flex justify-between">
              <span>Тип</span>
              <span className="text-gray-200 font-mono">{persona.entity_type}</span>
            </div>
            <div className="flex justify-between">
              <span>Уровень AI</span>
              <span className={TIER_COLOR[persona.preferred_tier] ?? "text-gray-300"}>
                Tier {persona.preferred_tier} · {TIER_LABEL[persona.preferred_tier]}
              </span>
            </div>
            {persona.preferred_model && (
              <div className="flex justify-between">
                <span>Модель</span>
                <span className="text-gray-200 font-mono text-xs">{persona.preferred_model}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span>Диалогов</span>
              <span className="text-gray-200">{persona.total_conversations}</span>
            </div>
          </div>

          {!persona.is_default && (
            <button
              onClick={toggleEnabled}
              className={clsx(
                "w-full rounded-lg text-sm font-medium py-2 transition-colors",
                persona.is_enabled
                  ? "bg-red-900/40 hover:bg-red-900/60 text-red-400 border border-red-800/50"
                  : "bg-green-900/40 hover:bg-green-900/60 text-green-400 border border-green-800/50"
              )}
            >
              {persona.is_enabled ? "Отключить агента" : "Включить агента"}
            </button>
          )}
          {persona.is_default && (
            <p className="text-xs text-gray-600 text-center">Системный агент — нельзя отключить</p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Persona card ──────────────────────────────────────────────────────────────
function PersonaCard({
  persona,
  token,
  onUpdate,
}: {
  persona: AgentPersona;
  token: string;
  onUpdate: (p: AgentPersona) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={clsx(
        "rounded-xl border transition-colors",
        !persona.is_enabled ? "opacity-50 bg-gray-900/50 border-gray-800/50" : "bg-gray-900 border-gray-800"
      )}
    >
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3.5 text-left"
      >
        <span className="text-2xl flex-shrink-0">{persona.avatar_emoji}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-gray-200">{persona.display_name}</span>
            {persona.is_default && (
              <span className="text-xs bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded">system</span>
            )}
            {!persona.is_enabled && (
              <span className="text-xs bg-red-900/40 text-red-500 px-1.5 py-0.5 rounded">disabled</span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-0.5">
            <span className="text-xs text-gray-600 font-mono">{persona.entity_type}</span>
            {persona.training_context_length > 0 && (
              <span className="text-xs text-indigo-500">
                📚 {persona.training_context_length} симв.
              </span>
            )}
            {persona.knowledge_base_count > 0 && (
              <span className="text-xs text-green-600">
                🗂 {persona.knowledge_base_count} docs
              </span>
            )}
          </div>
        </div>
        <span className={clsx("text-xs flex-shrink-0", TIER_COLOR[persona.preferred_tier] ?? "text-gray-600")}>
          T{persona.preferred_tier}
        </span>
        <span className="text-gray-600 text-xs flex-shrink-0 ml-1">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="px-4 pb-4">
          <PersonaDetail persona={persona} token={token} onUpdate={onUpdate} />
        </div>
      )}
    </div>
  );
}

// ── Create persona form ───────────────────────────────────────────────────────
function CreatePersonaForm({
  token,
  onCreated,
  onCancel,
}: {
  token: string;
  onCreated: (p: AgentPersona) => void;
  onCancel: () => void;
}) {
  const [displayName, setDisplayName] = useState("");
  const [entityType, setEntityType] = useState("");
  const [emoji, setEmoji] = useState("🤖");
  const [description, setDescription] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [tier, setTier] = useState(2);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!displayName.trim() || !entityType.trim()) return;
    setLoading(true);
    setError("");
    try {
      const persona = await api.adminAgents.create(
        {
          name: displayName.trim(),
          display_name: displayName.trim(),
          entity_type: entityType.trim().toLowerCase().replace(/\s+/g, "_"),
          avatar_emoji: emoji,
          description: description || undefined,
          system_prompt: systemPrompt || undefined,
          preferred_tier: tier,
        },
        token
      ) as AgentPersona;
      onCreated(persona);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка создания");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl bg-gray-900 border border-indigo-800/50 p-5 space-y-4"
    >
      <p className="text-sm font-semibold text-indigo-300">Новый агент</p>

      <div className="grid grid-cols-[3rem_1fr] gap-3">
        <input
          value={emoji}
          onChange={(e) => setEmoji(e.target.value)}
          maxLength={2}
          className="rounded-lg bg-gray-800 border border-gray-700 text-center text-2xl focus:outline-none focus:border-indigo-500"
        />
        <input
          autoFocus
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder="Название агента"
          className="rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-200 px-3 py-2 focus:outline-none focus:border-indigo-500"
          required
        />
      </div>

      <div className="space-y-1">
        <label className="text-xs text-gray-500">entity_type (уникальный ID)</label>
        <input
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
          placeholder="my_custom_agent"
          className="w-full rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-300 font-mono px-3 py-2 focus:outline-none focus:border-indigo-500"
          required
        />
      </div>

      <input
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Описание агента (опционально)"
        className="w-full rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-300 px-3 py-2 focus:outline-none focus:border-indigo-500"
      />

      <div className="space-y-1">
        <label className="text-xs text-gray-500">System Prompt</label>
        <textarea
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
          rows={5}
          placeholder="You are a specialized assistant..."
          className="w-full rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-200 px-3 py-2 focus:outline-none focus:border-indigo-500 resize-none font-mono"
        />
      </div>

      <div className="space-y-1">
        <label className="text-xs text-gray-500">AI Tier</label>
        <select
          value={tier}
          onChange={(e) => setTier(Number(e.target.value))}
          className="w-full rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-300 px-3 py-2 focus:outline-none focus:border-indigo-500"
        >
          <option value={1}>Tier 1 — Механический (быстро, дёшево)</option>
          <option value={2}>Tier 2 — Аналитический (баланс)</option>
          <option value={3}>Tier 3 — Стратегический (мощно)</option>
        </select>
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={loading}
          className="flex-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium py-2 transition-colors"
        >
          {loading ? "Создаю..." : "Создать агента"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 text-sm px-4 py-2 transition-colors"
        >
          Отмена
        </button>
      </div>
    </form>
  );
}

// ── Main manager ──────────────────────────────────────────────────────────────
export function AgentsManager({
  initialPersonas,
  token,
}: {
  initialPersonas: AgentPersona[];
  token: string;
}) {
  const [personas, setPersonas] = useState(initialPersonas);
  const [showCreate, setShowCreate] = useState(false);

  function handleUpdate(updated: AgentPersona) {
    setPersonas((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  }

  function handleCreated(p: AgentPersona) {
    setPersonas((prev) => [...prev, p]);
    setShowCreate(false);
  }

  const enabled = personas.filter((p) => p.is_enabled).length;
  const custom = personas.filter((p) => !p.is_default).length;

  return (
    <div className="space-y-4">
      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 text-center">
          <p className="text-xl font-bold text-white">{personas.length}</p>
          <p className="text-xs text-gray-500 mt-0.5">Всего агентов</p>
        </div>
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 text-center">
          <p className="text-xl font-bold text-green-400">{enabled}</p>
          <p className="text-xs text-gray-500 mt-0.5">Активных</p>
        </div>
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 text-center">
          <p className="text-xl font-bold text-indigo-400">{custom}</p>
          <p className="text-xs text-gray-500 mt-0.5">Кастомных</p>
        </div>
      </div>

      {/* Persona list */}
      <div className="space-y-2">
        {personas.map((p) => (
          <PersonaCard key={p.id} persona={p} token={token} onUpdate={handleUpdate} />
        ))}
      </div>

      {/* Create form or button */}
      {showCreate ? (
        <CreatePersonaForm
          token={token}
          onCreated={handleCreated}
          onCancel={() => setShowCreate(false)}
        />
      ) : (
        <button
          onClick={() => setShowCreate(true)}
          className="w-full rounded-xl border border-dashed border-gray-700 hover:border-indigo-600 text-gray-600 hover:text-indigo-400 text-sm py-3 transition-colors"
        >
          + Добавить нового агента
        </button>
      )}
    </div>
  );
}
