/**
 * Tests for QuickQueue component.
 *
 * Mocks: @/lib/api (steps.listQuick, steps.createWitness)
 */
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { QuickQueue } from "@/components/QuickQueue";
import type { StepObject } from "@/lib/types";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockListQuick = jest.fn();
const mockCreateWitness = jest.fn();

jest.mock("@/lib/api", () => ({
  api: {
    steps: {
      listQuick: (...args: unknown[]) => mockListQuick(...args),
      createWitness: (...args: unknown[]) => mockCreateWitness(...args),
    },
  },
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeStep(overrides: Partial<StepObject> = {}): StepObject {
  return {
    id: "step-1",
    title: "Buy groceries",
    step_type: "focus_step",
    estimated_minutes: 10,
    status: "active",
    decision_id: "dec-1",
    execution_readiness: "ready",
    definition_of_done_ref: null,
    step_order: 0,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderQueue(steps: StepObject[] = [makeStep()]) {
  return render(<QuickQueue initialSteps={steps} token="test-token" />);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("QuickQueue", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockCreateWitness.mockResolvedValue({});
    mockListQuick.mockResolvedValue([]);
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it("renders step titles", () => {
    renderQueue([makeStep({ id: "s1", title: "Write tests" }), makeStep({ id: "s2", title: "Deploy app" })]);
    expect(screen.getByText("Write tests")).toBeInTheDocument();
    expect(screen.getByText("Deploy app")).toBeInTheDocument();
  });

  it("shows empty state when no steps", () => {
    renderQueue([]);
    expect(screen.getByText(/Нет быстрых задач/)).toBeInTheDocument();
    expect(screen.getByText(/Все быстрые задачи выполнены/)).toBeInTheDocument();
  });

  it("shows step count in header", () => {
    renderQueue([makeStep({ id: "s1" }), makeStep({ id: "s2" })]);
    expect(screen.getByText(/2 задач/)).toBeInTheDocument();
  });

  it("shows Готово button for each step", () => {
    renderQueue([makeStep({ id: "s1", title: "Task A" }), makeStep({ id: "s2", title: "Task B" })]);
    const buttons = screen.getAllByText("Готово");
    expect(buttons).toHaveLength(2);
  });

  it("clicking Готово calls api.steps.createWitness with correct args", async () => {
    renderQueue([makeStep({ id: "step-abc" })]);

    await act(async () => {
      fireEvent.click(screen.getByText("Готово"));
    });

    await waitFor(() => {
      expect(mockCreateWitness).toHaveBeenCalledWith(
        "step-abc",
        expect.objectContaining({
          witness_type: "manual",
          verification_class: "reported",
        }),
        "test-token"
      );
    });
  });

  it("step gets done styling after successful complete", async () => {
    renderQueue([makeStep({ id: "step-xyz", title: "Important task" })]);

    await act(async () => {
      fireEvent.click(screen.getByText("Готово"));
    });

    await waitFor(() => {
      // The ✓ checkmark indicates done state
      expect(screen.getByText("✓")).toBeInTheDocument();
    });
  });

  it("step is removed from list after animation delay", async () => {
    renderQueue([makeStep({ id: "step-rem", title: "Remove me" })]);

    await act(async () => {
      fireEvent.click(screen.getByText("Готово"));
    });

    // Step is still visible (animated state)
    expect(screen.getByText("Remove me")).toBeInTheDocument();

    // Advance past the 600ms removal delay
    await act(async () => {
      jest.advanceTimersByTime(700);
    });

    expect(screen.queryByText("Remove me")).not.toBeInTheDocument();
  });

  it("clicking refresh button calls api.steps.listQuick", async () => {
    const refreshedStep = makeStep({ id: "s-new", title: "New task" });
    mockListQuick.mockResolvedValue([refreshedStep]);

    renderQueue([]);

    await act(async () => {
      fireEvent.click(screen.getByText("↻ Обновить"));
    });

    await waitFor(() => {
      expect(mockListQuick).toHaveBeenCalledWith("test-token");
    });
  });

  it("refresh button shows loading state while fetching", async () => {
    let resolveRefresh!: (v: StepObject[]) => void;
    mockListQuick.mockReturnValue(new Promise((r) => { resolveRefresh = r; }));

    renderQueue([]);

    fireEvent.click(screen.getByText("↻ Обновить"));
    expect(await screen.findByText("Обновляю…")).toBeInTheDocument();

    await act(async () => {
      resolveRefresh([]);
    });

    expect(screen.queryByText("Обновляю…")).not.toBeInTheDocument();
  });

  it("refresh updates step list with new data", async () => {
    const newStep = makeStep({ id: "fresh-1", title: "Fresh task" });
    mockListQuick.mockResolvedValue([newStep]);

    renderQueue([makeStep({ id: "old-1", title: "Old task" })]);

    await act(async () => {
      fireEvent.click(screen.getByText("↻ Обновить"));
    });

    await waitFor(() => {
      expect(screen.getByText("Fresh task")).toBeInTheDocument();
      expect(screen.queryByText("Old task")).not.toBeInTheDocument();
    });
  });

  it("shows type badge label for focus_step", () => {
    renderQueue([makeStep({ step_type: "focus_step" })]);
    expect(screen.getByText("фокус")).toBeInTheDocument();
  });

  it("shows type badge label for rescue_entry_step", () => {
    renderQueue([makeStep({ step_type: "rescue_entry_step" })]);
    expect(screen.getByText("срочно")).toBeInTheDocument();
  });

  it("shows estimated minutes when present", () => {
    renderQueue([makeStep({ estimated_minutes: 12 })]);
    expect(screen.getByText("12 мин")).toBeInTheDocument();
  });

  it("API failure on complete does not crash — step remains", async () => {
    mockCreateWitness.mockRejectedValue(new Error("Network error"));
    renderQueue([makeStep({ id: "stay-1", title: "Stay visible" })]);

    await act(async () => {
      fireEvent.click(screen.getByText("Готово"));
    });

    await waitFor(() => {
      expect(mockCreateWitness).toHaveBeenCalled();
    });

    // Step still visible after error
    expect(screen.getByText("Stay visible")).toBeInTheDocument();
  });
});
