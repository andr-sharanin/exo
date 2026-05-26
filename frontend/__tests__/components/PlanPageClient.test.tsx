/**
 * Tests for PlanPageClient component.
 *
 * Mocks: @/lib/api (secretary.*), next/navigation, @/hooks/useSSE,
 *        @/components/DailyPlanCard (stub)
 */
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { PlanPageClient } from "@/components/PlanPageClient";
import type { DayPlan } from "@/lib/types";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockGeneratePlan = jest.fn();
const mockPlanJobStatus = jest.fn();
const mockTodayPlan = jest.fn();

jest.mock("@/lib/api", () => ({
  api: {
    secretary: {
      generatePlan: (...args: unknown[]) => mockGeneratePlan(...args),
      planJobStatus: (...args: unknown[]) => mockPlanJobStatus(...args),
      todayPlan: (...args: unknown[]) => mockTodayPlan(...args),
    },
  },
}));

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), refresh: jest.fn() }),
}));

// Capture the SSE handler so tests can fire SSE events manually
let capturedSSEHandler: ((e: { type: string; payload: Record<string, unknown> }) => void) | null = null;

jest.mock("@/hooks/useSSE", () => ({
  useSSE: (handler: (e: { type: string; payload: Record<string, unknown> }) => void) => {
    capturedSSEHandler = handler;
  },
}));

// Stub DailyPlanCard — we only need to verify it receives the plan
jest.mock("@/components/DailyPlanCard", () => ({
  DailyPlanCard: ({ plan }: { plan: { id: string } }) => (
    <div data-testid="daily-plan-card">{plan.id}</div>
  ),
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makePlan(id = "plan-1"): DayPlan {
  return {
    id,
    plan_date: "2026-01-01",
    status: "draft",
    items: [],
    energy_state_at_generation: null,
    system_mode_at_generation: null,
    total_estimated_minutes: 0,
    generated_at: "2026-01-01T08:00:00Z",
    accepted_at: null,
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderClient(initialPlan: DayPlan | null = null) {
  return render(<PlanPageClient initialPlan={initialPlan} token="test-token" />);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("PlanPageClient", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    capturedSSEHandler = null;
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  // ── Initial render ─────────────────────────────────────────────────────────

  it("shows 'Сгенерировать план' button when no plan", () => {
    renderClient(null);
    expect(screen.getByText("Сгенерировать план")).toBeInTheDocument();
  });

  it("shows 'Пересобрать' button when plan exists", () => {
    renderClient(makePlan());
    expect(screen.getByText("Пересобрать")).toBeInTheDocument();
  });

  it("renders DailyPlanCard with initialPlan when provided", () => {
    renderClient(makePlan("plan-42"));
    expect(screen.getByTestId("daily-plan-card")).toHaveTextContent("plan-42");
  });

  it("shows no plan message when initialPlan is null", () => {
    renderClient(null);
    expect(screen.getByText(/На сегодня нет плана/)).toBeInTheDocument();
  });

  // ── Generate flow ──────────────────────────────────────────────────────────

  it("clicking generate calls api.secretary.generatePlan", async () => {
    mockGeneratePlan.mockResolvedValue({ job_id: "job-1", status: "queued" });
    mockPlanJobStatus.mockResolvedValue({ status: "queued" });

    renderClient(null);

    await act(async () => {
      fireEvent.click(screen.getByText("Сгенерировать план"));
    });

    await waitFor(() => {
      expect(mockGeneratePlan).toHaveBeenCalledWith("test-token", false);
    });
  });

  it("clicking Пересобрать passes regenerate=true", async () => {
    mockGeneratePlan.mockResolvedValue({ job_id: "job-r", status: "queued" });
    mockPlanJobStatus.mockResolvedValue({ status: "queued" });

    renderClient(makePlan());

    await act(async () => {
      fireEvent.click(screen.getByText("Пересобрать"));
    });

    await waitFor(() => {
      expect(mockGeneratePlan).toHaveBeenCalledWith("test-token", true);
    });
  });

  it("shows spinner and 'Генерирую' text while generating", async () => {
    let resolveGenerate!: (v: { job_id: string; status: string }) => void;
    mockGeneratePlan.mockReturnValue(
      new Promise((r) => { resolveGenerate = r; })
    );

    renderClient(null);

    fireEvent.click(screen.getByText("Сгенерировать план"));

    await waitFor(() => {
      expect(screen.getByText("Генерирую")).toBeInTheDocument();
    });

    // Button disabled while generating
    const btn = screen.getByRole("button", { name: /Генерирую/ });
    expect(btn).toBeDisabled();

    await act(async () => {
      resolveGenerate({ job_id: "job-1", status: "queued" });
    });
  });

  it("shows polling progress indicator", async () => {
    mockGeneratePlan.mockResolvedValue({ job_id: "job-2", status: "queued" });
    mockPlanJobStatus.mockResolvedValue({ status: "running" });

    renderClient(null);

    await act(async () => {
      fireEvent.click(screen.getByText("Сгенерировать план"));
    });

    // Advance past transition + first poll
    await act(async () => {
      jest.advanceTimersByTime(3500);
    });

    // Should show "Генерирую…" polling indicator
    await waitFor(() => {
      expect(screen.getByText(/Генерирую…/)).toBeInTheDocument();
    });
  });

  it("shows error message on generatePlan API failure", async () => {
    mockGeneratePlan.mockRejectedValue(new Error("Server down"));

    renderClient(null);

    await act(async () => {
      fireEvent.click(screen.getByText("Сгенерировать план"));
    });

    await waitFor(() => {
      expect(screen.getByText("Server down")).toBeInTheDocument();
    });
  });

  it("dismissing error via Закрыть hides the error panel", async () => {
    mockGeneratePlan.mockRejectedValue(new Error("Timeout"));

    renderClient(null);

    await act(async () => {
      fireEvent.click(screen.getByText("Сгенерировать план"));
    });

    await waitFor(() => {
      expect(screen.getByText("Timeout")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Закрыть"));
    expect(screen.queryByText("Timeout")).not.toBeInTheDocument();
  });

  // ── Polling completion ─────────────────────────────────────────────────────

  it("fetches plan after job reports complete", async () => {
    const plan = makePlan("poll-done");
    mockGeneratePlan.mockResolvedValue({ job_id: "job-3", status: "queued" });
    mockPlanJobStatus.mockResolvedValue({ status: "complete" });
    mockTodayPlan.mockResolvedValue(plan);

    renderClient(null);

    await act(async () => {
      fireEvent.click(screen.getByText("Сгенерировать план"));
    });

    await act(async () => {
      jest.advanceTimersByTime(3500);
    });

    await waitFor(() => {
      expect(mockTodayPlan).toHaveBeenCalledWith("test-token");
    });

    await waitFor(() => {
      expect(screen.getByTestId("daily-plan-card")).toHaveTextContent("poll-done");
    });
  });

  it("shows error when job status returns failed", async () => {
    mockGeneratePlan.mockResolvedValue({ job_id: "job-4", status: "queued" });
    mockPlanJobStatus.mockResolvedValue({ status: "failed" });

    renderClient(null);

    await act(async () => {
      fireEvent.click(screen.getByText("Сгенерировать план"));
    });

    await act(async () => {
      jest.advanceTimersByTime(3500);
    });

    await waitFor(() => {
      expect(screen.getByText(/завершилась с ошибкой/)).toBeInTheDocument();
    });
  });

  // ── SSE events ─────────────────────────────────────────────────────────────

  it("plan_ready SSE event triggers plan fetch", async () => {
    const plan = makePlan("sse-plan");
    mockTodayPlan.mockResolvedValue(plan);
    mockGeneratePlan.mockResolvedValue({ job_id: "job-sse", status: "queued" });
    mockPlanJobStatus.mockResolvedValue({ status: "running" });

    renderClient(null);

    await act(async () => {
      fireEvent.click(screen.getByText("Сгенерировать план"));
    });

    await waitFor(() => expect(capturedSSEHandler).not.toBeNull());

    await act(async () => {
      capturedSSEHandler!({ type: "plan_ready", payload: {} });
    });

    await waitFor(() => {
      expect(mockTodayPlan).toHaveBeenCalledWith("test-token");
    });

    await waitFor(() => {
      expect(screen.getByTestId("daily-plan-card")).toHaveTextContent("sse-plan");
    });
  });

  it("job_failed SSE event shows error message", async () => {
    mockGeneratePlan.mockResolvedValue({ job_id: "job-f", status: "queued" });
    mockPlanJobStatus.mockResolvedValue({ status: "running" });

    renderClient(null);

    await act(async () => {
      fireEvent.click(screen.getByText("Сгенерировать план"));
    });

    await waitFor(() => expect(capturedSSEHandler).not.toBeNull());

    await act(async () => {
      capturedSSEHandler!({ type: "job_failed", payload: { job: "generate_plan" } });
    });

    await waitFor(() => {
      expect(screen.getByText(/Генерация плана не удалась/)).toBeInTheDocument();
    });
  });
});
