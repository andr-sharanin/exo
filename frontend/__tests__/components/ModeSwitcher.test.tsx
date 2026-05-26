/**
 * Tests for ModeSwitcher component.
 *
 * Mocks: @/lib/api (modes.switch)
 */
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ModeSwitcher } from "@/components/ModeSwitcher";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockModeSwitch = jest.fn();

jest.mock("@/lib/api", () => ({
  api: {
    modes: {
      switch: (...args: unknown[]) => mockModeSwitch(...args),
    },
  },
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderSwitcher(initialMode: string | null = "harmony") {
  return render(<ModeSwitcher initialMode={initialMode} token="test-token" />);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("ModeSwitcher", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockModeSwitch.mockResolvedValue({});
  });

  it("renders all 7 mode cards", () => {
    renderSwitcher();
    const modeLabels = [
      "Достигатор",
      "Гармония",
      "Восстановление",
      "Обучение",
      "Прояснение",
      "Кризис",
      "Творческий",
    ];
    modeLabels.forEach((label) => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });

  it("shows current mode banner with active label", () => {
    renderSwitcher("achiever");
    expect(screen.getByText("Активный режим")).toBeInTheDocument();
    expect(screen.getByText("Достигатор")).toBeInTheDocument();
  });

  it("shows no-mode fallback when initialMode is null", () => {
    renderSwitcher(null);
    expect(screen.getByText(/Режим не выбран/)).toBeInTheDocument();
  });

  it("marks current mode card as active (disabled)", () => {
    renderSwitcher("harmony");
    // The harmony button should show "● Активен" label
    expect(screen.getAllByText("● Активен")).toHaveLength(1);
  });

  it("clicking a non-active mode shows confirm panel", async () => {
    renderSwitcher("harmony");
    // Click on "Достигатор" (not current mode)
    fireEvent.click(screen.getAllByText("Достигатор")[0]);
    expect(await screen.findByText(/Переключить на/)).toBeInTheDocument();
    expect(screen.getByText("Подтвердить")).toBeInTheDocument();
    expect(screen.getByText("Отмена")).toBeInTheDocument();
  });

  it("clicking active mode does not show confirm panel", () => {
    renderSwitcher("harmony");
    // The harmony button is disabled — clicking should not open confirm panel
    fireEvent.click(screen.getAllByText("Гармония")[0]);
    expect(screen.queryByText("Подтвердить")).not.toBeInTheDocument();
  });

  it("cancel button closes confirm panel", async () => {
    renderSwitcher("harmony");
    fireEvent.click(screen.getAllByText("Достигатор")[0]);
    expect(await screen.findByText("Подтвердить")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Отмена"));
    expect(screen.queryByText("Подтвердить")).not.toBeInTheDocument();
  });

  it("confirm button calls api.modes.switch with selected mode", async () => {
    renderSwitcher("harmony");
    fireEvent.click(screen.getAllByText("Достигатор")[0]);
    await screen.findByText("Подтвердить");

    await act(async () => {
      fireEvent.click(screen.getByText("Подтвердить"));
    });

    await waitFor(() => {
      expect(mockModeSwitch).toHaveBeenCalledWith(
        expect.objectContaining({ mode: "achiever" }),
        "test-token"
      );
    });
  });

  it("includes reason in switch call when entered", async () => {
    renderSwitcher("harmony");
    fireEvent.click(screen.getAllByText("Достигатор")[0]);
    await screen.findByText("Подтвердить");

    const textarea = screen.getByPlaceholderText(/Причина переключения/);
    await userEvent.type(textarea, "Дедлайн сегодня");

    await act(async () => {
      fireEvent.click(screen.getByText("Подтвердить"));
    });

    await waitFor(() => {
      expect(mockModeSwitch).toHaveBeenCalledWith(
        expect.objectContaining({ mode: "achiever", reason: "Дедлайн сегодня" }),
        "test-token"
      );
    });
  });

  it("updates current mode after successful switch", async () => {
    renderSwitcher("harmony");
    fireEvent.click(screen.getAllByText("Достигатор")[0]);
    await screen.findByText("Подтвердить");

    await act(async () => {
      fireEvent.click(screen.getByText("Подтвердить"));
    });

    await waitFor(() => {
      // Banner now shows "Достигатор" as active
      expect(screen.getAllByText("Достигатор").length).toBeGreaterThan(0);
    });
    // Confirm panel should be gone
    expect(screen.queryByText("Подтвердить")).not.toBeInTheDocument();
  });

  it("shows error message on API failure", async () => {
    mockModeSwitch.mockRejectedValue(new Error("Network error"));
    renderSwitcher("harmony");
    fireEvent.click(screen.getAllByText("Достигатор")[0]);
    await screen.findByText("Подтвердить");

    await act(async () => {
      fireEvent.click(screen.getByText("Подтвердить"));
    });

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });
});
