import {
  buildFastApiUrl,
  getFastApiBaseUrl,
  getFastApiJson,
  postFastApiJson,
  readFastApiError,
} from "@/shared/api/fastapi-client";

describe("fastapi client", () => {
  const originalBaseUrl = process.env.NEXT_PUBLIC_FASTAPI_BASE_URL;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_FASTAPI_BASE_URL = "http://localhost:8000/";
  });

  afterEach(() => {
    vi.restoreAllMocks();

    if (originalBaseUrl === undefined) {
      delete process.env.NEXT_PUBLIC_FASTAPI_BASE_URL;
    } else {
      process.env.NEXT_PUBLIC_FASTAPI_BASE_URL = originalBaseUrl;
    }
  });

  it("builds direct FastAPI URLs from the public base URL", () => {
    expect(getFastApiBaseUrl()).toBe("http://localhost:8000");
    expect(buildFastApiUrl("/route-analysis")).toBe("http://localhost:8000/route-analysis");
  });

  it("posts JSON directly to FastAPI", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "ok" }),
      }),
    );

    const response = await postFastApiJson<{ status: string }>("/voice-parse", {
      transcript: "Union Square to Lincoln Center",
    });

    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/voice-parse",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(response.status).toBe("ok");
  });

  it("reads GET responses directly from FastAPI", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "ok" }),
      }),
    );

    const response = await getFastApiJson<{ status: string }>("/health");

    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/health",
      expect.objectContaining({
        method: "GET",
      }),
    );
    expect(response.status).toBe("ok");
  });

  it("normalizes FastAPI detail payloads into readable errors", () => {
    expect(readFastApiError({ detail: "Origin is required." })).toBe("Origin is required.");
    expect(readFastApiError({ detail: [{ msg: "Field required" }] })).toBe("Field required");
    expect(readFastApiError({ error: "Service unavailable" })).toBe("Service unavailable");
  });

  it("throws a clear configuration error when the public FastAPI URL is missing", () => {
    delete process.env.NEXT_PUBLIC_FASTAPI_BASE_URL;

    expect(() => getFastApiBaseUrl()).toThrow("NEXT_PUBLIC_FASTAPI_BASE_URL is not configured.");
  });
});
