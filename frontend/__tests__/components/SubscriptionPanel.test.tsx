/**
 * Tests for SubscriptionPanel component.
 *
 * Mocks: @/lib/api (subscriptions.checkout, subscriptions.portal)
 */
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { SubscriptionPanel } from "@/components/SubscriptionPanel";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockCheckout = jest.fn();
const mockPortal = jest.fn();

jest.mock("@/lib/api", () => ({
  api: {
    subscriptions: {
      checkout: (...args: unknown[]) => mockCheckout(...args),
      portal: (...args: unknown[]) => mockPortal(...args),
    },
  },
}));

// Mock window.location.href assignment
const originalLocation = window.location;
beforeAll(() => {
  Object.defineProperty(window, "location", {
    configurable: true,
    value: { ...originalLocation, origin: "https://app.test", href: "" },
    writable: true,
  });
});
afterAll(() => {
  Object.defineProperty(window, "location", {
    configurable: true,
    value: originalLocation,
  });
});

// ── Fixtures ──────────────────────────────────────────────────────────────────

const freeTierData = {
  tier: "free",
  status: "free",
  current_period_end: null,
  trial_end: null,
  limits: {
    max_active_goals: 10,
    max_held_deposits: 5,
    allow_x2_governance: false,
    max_calendar_integrations: 1,
  },
};

const proTierData = {
  tier: "pro",
  status: "active",
  current_period_end: "2026-12-31T00:00:00Z",
  trial_end: null,
  limits: {
    max_active_goals: null,
    max_held_deposits: null,
    allow_x2_governance: true,
    max_calendar_integrations: null,
  },
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("SubscriptionPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (window.location as { href: string }).href = "";
  });

  // ── Rendering ──────────────────────────────────────────────────────────────

  it("shows Free tier label for free plan", () => {
    render(<SubscriptionPanel initialData={freeTierData} token="test-token" />);
    expect(screen.getByText("Free")).toBeInTheDocument();
  });

  it("shows Pro tier label for pro plan", () => {
    render(<SubscriptionPanel initialData={proTierData} token="test-token" />);
    expect(screen.getByText("Pro")).toBeInTheDocument();
  });

  it("shows limit values for free tier", () => {
    render(<SubscriptionPanel initialData={freeTierData} token="test-token" />);
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("shows 'Без ограничений' for unlimited pro limits", () => {
    render(<SubscriptionPanel initialData={proTierData} token="test-token" />);
    const unlimited = screen.getAllByText("Без ограничений");
    expect(unlimited.length).toBeGreaterThanOrEqual(3);
  });

  it("shows x2 governance allowed for pro", () => {
    render(<SubscriptionPanel initialData={proTierData} token="test-token" />);
    expect(screen.getByText("✓ Включено")).toBeInTheDocument();
  });

  it("shows x2 governance not available for free", () => {
    render(<SubscriptionPanel initialData={freeTierData} token="test-token" />);
    expect(screen.getByText("✗ Недоступно")).toBeInTheDocument();
  });

  it("shows period end date for active pro subscription", () => {
    render(<SubscriptionPanel initialData={proTierData} token="test-token" />);
    expect(screen.getByText(/31/)).toBeInTheDocument();
  });

  // ── Free tier — upgrade actions ───────────────────────────────────────────

  it("shows upgrade buttons for free tier", () => {
    render(<SubscriptionPanel initialData={freeTierData} token="test-token" />);
    expect(screen.getByText("Upgrade → Pro")).toBeInTheDocument();
    expect(screen.getByText("Upgrade → Team")).toBeInTheDocument();
  });

  it("does not show upgrade buttons for pro tier", () => {
    render(<SubscriptionPanel initialData={proTierData} token="test-token" />);
    expect(screen.queryByText("Upgrade → Pro")).not.toBeInTheDocument();
  });

  it("clicking Upgrade → Pro calls subscriptions.checkout with plan=pro", async () => {
    mockCheckout.mockResolvedValue({ checkout_url: "https://checkout.stripe.com/pay/cs_test" });

    render(<SubscriptionPanel initialData={freeTierData} token="test-token" />);

    await act(async () => {
      fireEvent.click(screen.getByText("Upgrade → Pro"));
    });

    await waitFor(() => {
      expect(mockCheckout).toHaveBeenCalledWith(
        expect.objectContaining({ plan: "pro" }),
        "test-token"
      );
    });
  });

  it("clicking Upgrade → Team calls subscriptions.checkout with plan=team", async () => {
    mockCheckout.mockResolvedValue({ checkout_url: "https://checkout.stripe.com/pay/cs_test" });

    render(<SubscriptionPanel initialData={freeTierData} token="test-token" />);

    await act(async () => {
      fireEvent.click(screen.getByText("Upgrade → Team"));
    });

    await waitFor(() => {
      expect(mockCheckout).toHaveBeenCalledWith(
        expect.objectContaining({ plan: "team" }),
        "test-token"
      );
    });
  });

  it("checkout includes correct success/cancel URLs", async () => {
    mockCheckout.mockResolvedValue({ checkout_url: "https://stripe.com/pay" });

    render(<SubscriptionPanel initialData={freeTierData} token="test-token" />);

    await act(async () => {
      fireEvent.click(screen.getByText("Upgrade → Pro"));
    });

    await waitFor(() => {
      expect(mockCheckout).toHaveBeenCalledWith(
        expect.objectContaining({
          success_url: expect.stringContaining("/settings/subscription"),
          cancel_url: expect.stringContaining("/settings/subscription"),
        }),
        "test-token"
      );
    });
  });

  it("redirects to checkout_url after successful checkout", async () => {
    mockCheckout.mockResolvedValue({ checkout_url: "https://checkout.stripe.com/cs_test" });

    render(<SubscriptionPanel initialData={freeTierData} token="test-token" />);

    await act(async () => {
      fireEvent.click(screen.getByText("Upgrade → Pro"));
    });

    await waitFor(() => {
      expect((window.location as { href: string }).href).toBe(
        "https://checkout.stripe.com/cs_test"
      );
    });
  });

  it("shows error when checkout fails", async () => {
    mockCheckout.mockRejectedValue(new Error("Stripe not configured"));

    render(<SubscriptionPanel initialData={freeTierData} token="test-token" />);

    await act(async () => {
      fireEvent.click(screen.getByText("Upgrade → Pro"));
    });

    await waitFor(() => {
      expect(screen.getByText("Stripe not configured")).toBeInTheDocument();
    });
  });

  // ── Paid tier — portal action ─────────────────────────────────────────────

  it("shows 'Управление подпиской' button for pro tier", () => {
    render(<SubscriptionPanel initialData={proTierData} token="test-token" />);
    expect(screen.getByText("Управление подпиской →")).toBeInTheDocument();
  });

  it("clicking portal button calls subscriptions.portal", async () => {
    mockPortal.mockResolvedValue({ portal_url: "https://billing.stripe.com/portal" });

    render(<SubscriptionPanel initialData={proTierData} token="test-token" />);

    await act(async () => {
      fireEvent.click(screen.getByText("Управление подпиской →"));
    });

    await waitFor(() => {
      expect(mockPortal).toHaveBeenCalledWith(
        "test-token",
        expect.stringContaining("/settings/subscription")
      );
    });
  });

  it("redirects to portal_url after successful portal request", async () => {
    mockPortal.mockResolvedValue({ portal_url: "https://billing.stripe.com/p/test" });

    render(<SubscriptionPanel initialData={proTierData} token="test-token" />);

    await act(async () => {
      fireEvent.click(screen.getByText("Управление подпиской →"));
    });

    await waitFor(() => {
      expect((window.location as { href: string }).href).toBe(
        "https://billing.stripe.com/p/test"
      );
    });
  });

  it("shows error when portal call fails", async () => {
    mockPortal.mockRejectedValue(new Error("No Stripe customer linked"));

    render(<SubscriptionPanel initialData={proTierData} token="test-token" />);

    await act(async () => {
      fireEvent.click(screen.getByText("Управление подпиской →"));
    });

    await waitFor(() => {
      expect(screen.getByText("No Stripe customer linked")).toBeInTheDocument();
    });
  });
});
