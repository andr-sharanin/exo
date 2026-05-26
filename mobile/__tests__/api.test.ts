// TDD RED — written before implementation
import { api } from "../lib/api";

global.fetch = jest.fn();

const TOKEN = "test-bearer-token";

function mockOk(body: unknown) {
  (fetch as jest.Mock).mockResolvedValue({
    ok: true,
    json: async () => body,
  });
}

function mockFail(status: number) {
  (fetch as jest.Mock).mockResolvedValue({
    ok: false,
    status,
    json: async () => ({}),
  });
}

beforeEach(() => (fetch as jest.Mock).mockClear());

describe("api.energy", () => {
  test("checkin sends POST to /energy/checkin with Bearer token", async () => {
    mockOk({ composite_score: 75, energy_state: "sufficient" });
    await api.energy.checkin({ sleep_quality: 3, mood: 4, energy_level: 3 }, TOKEN);

    const [url, opts] = (fetch as jest.Mock).mock.calls[0];
    expect(url).toContain("/energy/checkin");
    expect(opts.method).toBe("POST");
    expect(opts.headers["Authorization"]).toBe(`Bearer ${TOKEN}`);
  });

  test("checkin sends correct body", async () => {
    mockOk({});
    await api.energy.checkin({ sleep_quality: 2, mood: 4, energy_level: 3 }, TOKEN);

    const body = JSON.parse((fetch as jest.Mock).mock.calls[0][1].body);
    expect(body).toEqual({ sleep_quality: 2, mood: 4, energy_level: 3 });
  });

  test("getScore sends GET to /energy/score", async () => {
    mockOk({ composite_score: 80 });
    await api.energy.getScore(TOKEN);

    const [url, opts] = (fetch as jest.Mock).mock.calls[0];
    expect(url).toContain("/energy/score");
    expect(opts.headers["Authorization"]).toBe(`Bearer ${TOKEN}`);
  });
});

describe("api.commands", () => {
  test("create sends POST with raw_input", async () => {
    mockOk({ id: "cmd-1" });
    await api.commands.create({ raw_input: "buy milk" }, TOKEN);

    const [url, opts] = (fetch as jest.Mock).mock.calls[0];
    expect(url).toContain("/commands");
    expect(opts.method).toBe("POST");
    expect(JSON.parse(opts.body).raw_input).toBe("buy milk");
  });
});

describe("api.secretary", () => {
  test("getTodayPlan sends GET to /secretary/plan/today", async () => {
    mockOk({ id: "plan-1", status: "draft" });
    await api.secretary.getTodayPlan(TOKEN);

    expect((fetch as jest.Mock).mock.calls[0][0]).toContain("/secretary/plan/today");
  });

  test("generatePlan sends POST to /secretary/plan", async () => {
    mockOk({ id: "plan-2", status: "draft" });
    await api.secretary.generatePlan(TOKEN);

    const [url, opts] = (fetch as jest.Mock).mock.calls[0];
    expect(url).toContain("/secretary/plan");
    expect(opts.method).toBe("POST");
  });
});

describe("api error handling", () => {
  test("throws with HTTP status on non-ok response", async () => {
    mockFail(401);
    await expect(api.energy.getScore(TOKEN)).rejects.toThrow("HTTP 401");
  });

  test("throws on 422 validation error", async () => {
    mockFail(422);
    await expect(api.commands.create({ raw_input: "" }, TOKEN)).rejects.toThrow("HTTP 422");
  });
});
