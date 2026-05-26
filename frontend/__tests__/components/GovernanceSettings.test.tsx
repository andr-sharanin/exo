/**
 * Tests for GovernanceSettings component.
 *
 * Mocks: @/lib/api (governance.updatePolicy, governance.createRecord)
 */
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GovernanceSettings } from "@/components/GovernanceSettings";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockUpdatePolicy = jest.fn();
const mockCreateRecord = jest.fn();

jest.mock("@/lib/api", () => ({
  api: {
    governance: {
      updatePolicy: (...args: unknown[]) => mockUpdatePolicy(...args),
      createRecord: (...args: unknown[]) => mockCreateRecord(...args),
    },
  },
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const soloPolicy = {
  id: "pol-1",
  user_id: "user-1",
  mode: "solo" as const,
  partner_email: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const x2Policy = {
  ...soloPolicy,
  id: "pol-2",
  mode: "x2" as const,
  partner_email: "partner@example.com",
};

const sampleRecord = {
  id: "rec-1",
  subject: "Skip gym today",
  reason: "Injured knee — doctor advised no exercise",
  mode_at_time: "solo",
  partner_email: null as string | null,
  status: "self_approved",
  approved_at: null,
  created_at: "2026-01-15T10:00:00Z",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const noRecords: (typeof sampleRecord)[] = [];

type PolicyFixture = { id: string; user_id: string; mode: "solo" | "x2"; partner_email: string | null; created_at: string; updated_at: string };

function renderSettings({
  policy = soloPolicy as PolicyFixture,
  records = noRecords,
}: { policy?: PolicyFixture; records?: (typeof sampleRecord)[] } = {}) {
  return render(
    <GovernanceSettings
      initialPolicy={policy}
      initialRecords={records}
      token="test-token"
    />
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("GovernanceSettings", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUpdatePolicy.mockResolvedValue({ ...soloPolicy });
    mockCreateRecord.mockResolvedValue({ ...sampleRecord });
  });

  // ── Policy section ─────────────────────────────────────────────────────────

  it("renders Solo and x2 mode buttons", () => {
    renderSettings();
    expect(screen.getByText("Solo")).toBeInTheDocument();
    expect(screen.getByText("x2 (партнёр)")).toBeInTheDocument();
  });

  it("shows partner email field when x2 policy is active", () => {
    renderSettings({ policy: x2Policy });
    expect(screen.getByPlaceholderText("partner@example.com")).toBeInTheDocument();
  });

  it("does not show partner email field for solo policy", () => {
    renderSettings({ policy: soloPolicy });
    expect(screen.queryByPlaceholderText("partner@example.com")).not.toBeInTheDocument();
  });

  it("clicking x2 button reveals partner email input", () => {
    renderSettings({ policy: soloPolicy });
    fireEvent.click(screen.getByText("x2 (партнёр)"));
    expect(screen.getByPlaceholderText("partner@example.com")).toBeInTheDocument();
  });

  it("save button is disabled when policy unchanged", () => {
    renderSettings({ policy: soloPolicy });
    const saveBtn = screen.getByText("Сохранить");
    expect(saveBtn).toBeDisabled();
  });

  it("save button enabled after changing mode", () => {
    renderSettings({ policy: soloPolicy });
    fireEvent.click(screen.getByText("x2 (партнёр)"));
    expect(screen.getByText("Сохранить")).not.toBeDisabled();
  });

  it("clicking save calls api.governance.updatePolicy", async () => {
    mockUpdatePolicy.mockResolvedValue({ ...soloPolicy, mode: "x2", partner_email: "new@test.com" });

    renderSettings({ policy: soloPolicy });
    fireEvent.click(screen.getByText("x2 (партнёр)"));

    const emailInput = screen.getByPlaceholderText("partner@example.com");
    await userEvent.clear(emailInput);
    await userEvent.type(emailInput, "new@test.com");

    await act(async () => {
      fireEvent.click(screen.getByText("Сохранить"));
    });

    await waitFor(() => {
      expect(mockUpdatePolicy).toHaveBeenCalledWith(
        expect.objectContaining({ mode: "x2", partner_email: "new@test.com" }),
        "test-token"
      );
    });
  });

  it("shows '✓ Сохранено' after successful save", async () => {
    renderSettings({ policy: soloPolicy });
    fireEvent.click(screen.getByText("x2 (партнёр)"));

    await act(async () => {
      fireEvent.click(screen.getByText("Сохранить"));
    });

    await waitFor(() => {
      expect(screen.getByText("✓ Сохранено")).toBeInTheDocument();
    });
  });

  it("shows error message when updatePolicy fails", async () => {
    mockUpdatePolicy.mockRejectedValue(new Error("Forbidden"));

    renderSettings({ policy: soloPolicy });
    fireEvent.click(screen.getByText("x2 (партнёр)"));

    await act(async () => {
      fireEvent.click(screen.getByText("Сохранить"));
    });

    await waitFor(() => {
      expect(screen.getByText("Forbidden")).toBeInTheDocument();
    });
  });

  // ── ADR form ───────────────────────────────────────────────────────────────

  it("ADR form is hidden initially", () => {
    renderSettings();
    expect(screen.queryByPlaceholderText(/откладываю задачу/i)).not.toBeInTheDocument();
  });

  it("clicking '+ Новый ADR' reveals the form", () => {
    renderSettings();
    fireEvent.click(screen.getByText("+ Новый ADR"));
    expect(
      screen.getByPlaceholderText(/откладываю задачу/i)
    ).toBeInTheDocument();
  });

  it("clicking 'Свернуть' hides the form", () => {
    renderSettings();
    fireEvent.click(screen.getByText("+ Новый ADR"));
    fireEvent.click(screen.getByText("Свернуть"));
    expect(screen.queryByPlaceholderText(/откладываю задачу/i)).not.toBeInTheDocument();
  });

  it("ADR submit button disabled when subject empty", () => {
    renderSettings();
    fireEvent.click(screen.getByText("+ Новый ADR"));
    // reason textarea starts empty too
    expect(screen.getByText("Записать")).toBeDisabled();
  });

  it("ADR submit button disabled when reason too short (<20 chars)", async () => {
    renderSettings();
    fireEvent.click(screen.getByText("+ Новый ADR"));

    await userEvent.type(
      screen.getByPlaceholderText(/откладываю задачу/i),
      "Subject here"
    );
    await userEvent.type(
      screen.getByPlaceholderText(/Почему принято/i),
      "short"
    );

    expect(screen.getByText("Записать")).toBeDisabled();
  });

  it("ADR submit button enabled with valid subject + reason ≥20 chars", async () => {
    renderSettings();
    fireEvent.click(screen.getByText("+ Новый ADR"));

    await userEvent.type(
      screen.getByPlaceholderText(/откладываю задачу/i),
      "Skip workout today"
    );
    await userEvent.type(
      screen.getByPlaceholderText(/Почему принято/i),
      "Knee injury, doctor advised rest"
    );

    expect(screen.getByText("Записать")).not.toBeDisabled();
  });

  it("submitting ADR calls api.governance.createRecord", async () => {
    renderSettings();
    fireEvent.click(screen.getByText("+ Новый ADR"));

    await userEvent.type(
      screen.getByPlaceholderText(/откладываю задачу/i),
      "Skip gym"
    );
    await userEvent.type(
      screen.getByPlaceholderText(/Почему принято/i),
      "Injured knee, rest advised by doctor"
    );

    await act(async () => {
      fireEvent.click(screen.getByText("Записать"));
    });

    await waitFor(() => {
      expect(mockCreateRecord).toHaveBeenCalledWith(
        expect.objectContaining({
          subject: "Skip gym",
          reason: "Injured knee, rest advised by doctor",
        }),
        "test-token"
      );
    });
  });

  it("after successful ADR creation form closes and record appears in log", async () => {
    renderSettings({ records: [] });
    fireEvent.click(screen.getByText("+ Новый ADR"));

    await userEvent.type(
      screen.getByPlaceholderText(/откладываю задачу/i),
      "Skip gym today"
    );
    await userEvent.type(
      screen.getByPlaceholderText(/Почему принято/i),
      "Injured knee — doctor advised no exercise"
    );

    await act(async () => {
      fireEvent.click(screen.getByText("Записать"));
    });

    await waitFor(() => {
      // Form should be gone
      expect(screen.queryByPlaceholderText(/откладываю задачу/i)).not.toBeInTheDocument();
      // New record subject appears in log
      expect(screen.getByText("Skip gym today")).toBeInTheDocument();
    });
  });

  it("shows error when createRecord fails", async () => {
    mockCreateRecord.mockRejectedValue(new Error("Validation error"));

    renderSettings();
    fireEvent.click(screen.getByText("+ Новый ADR"));

    await userEvent.type(
      screen.getByPlaceholderText(/откладываю задачу/i),
      "Test subject"
    );
    await userEvent.type(
      screen.getByPlaceholderText(/Почему принято/i),
      "A reason that is long enough for validation"
    );

    await act(async () => {
      fireEvent.click(screen.getByText("Записать"));
    });

    await waitFor(() => {
      expect(screen.getByText("Validation error")).toBeInTheDocument();
    });
  });

  // ── Records list ──────────────────────────────────────────────────────────

  it("shows empty state when no records", () => {
    renderSettings({ records: [] });
    expect(screen.getByText(/Нет записей/)).toBeInTheDocument();
  });

  it("renders existing records", () => {
    renderSettings({ records: [sampleRecord] });
    expect(screen.getByText("Skip gym today")).toBeInTheDocument();
    expect(screen.getByText("Injured knee — doctor advised no exercise")).toBeInTheDocument();
  });

  it("shows status label for self_approved record", () => {
    renderSettings({ records: [sampleRecord] });
    expect(screen.getByText("Подтверждено")).toBeInTheDocument();
  });

  it("shows status label for pending_partner record", () => {
    renderSettings({
      records: [{ ...sampleRecord, status: "pending_partner", partner_email: "p@ex.com" }],
    });
    expect(screen.getByText("Ожидает партнёра")).toBeInTheDocument();
  });

  it("shows 'Записать и отправить партнёру' button label in x2 mode", async () => {
    renderSettings({ policy: x2Policy });
    fireEvent.click(screen.getByText("+ Новый ADR"));
    expect(screen.getByText("Записать и отправить партнёру")).toBeInTheDocument();
  });
});
