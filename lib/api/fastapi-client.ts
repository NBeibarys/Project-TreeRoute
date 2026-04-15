export interface FastApiErrorPayload {
  detail?: unknown;
  error?: string;
  message?: string;
}

export function getFastApiBaseUrl(): string {
  const directFastApiBaseUrl = process.env.NEXT_PUBLIC_FASTAPI_BASE_URL?.trim() ?? "";
  if (!directFastApiBaseUrl) {
    throw new Error("NEXT_PUBLIC_FASTAPI_BASE_URL is not configured.");
  }

  return directFastApiBaseUrl.replace(/\/+$/, "");
}

export async function postFastApiJson<ResponsePayload>(
  path: string,
  body: unknown,
): Promise<ResponsePayload> {
  const response = await fetch(buildFastApiUrl(path), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  const payload = (await response.json()) as unknown;

  if (!response.ok) {
    throw new Error(readFastApiError(payload));
  }

  if (
    payload &&
    typeof payload === "object" &&
    "error" in payload &&
    typeof payload.error === "string" &&
    payload.error
  ) {
    throw new Error(payload.error);
  }

  return payload as ResponsePayload;
}

export async function getFastApiJson<ResponsePayload>(path: string): Promise<ResponsePayload> {
  const response = await fetch(buildFastApiUrl(path), {
    method: "GET",
  });

  const payload = (await response.json()) as unknown;
  if (!response.ok) {
    throw new Error(readFastApiError(payload));
  }

  return payload as ResponsePayload;
}

export function buildFastApiUrl(path: string): string {
  return new URL(path, `${getFastApiBaseUrl()}/`).toString();
}

export function readFastApiError(payload: unknown) {
  if (!payload || typeof payload !== "object") {
    return "FastAPI request failed.";
  }

  if ("error" in payload && typeof payload.error === "string" && payload.error.trim()) {
    return payload.error;
  }

  if ("message" in payload && typeof payload.message === "string" && payload.message.trim()) {
    return payload.message;
  }

  if ("detail" in payload) {
    const detail = formatDetailError(payload.detail);
    if (detail) {
      return detail;
    }
  }

  return "FastAPI request failed.";
}

function formatDetailError(detail: unknown): string | null {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (!Array.isArray(detail)) {
    return null;
  }

  const messages = detail
    .map((entry) => {
      if (!entry || typeof entry !== "object") {
        return null;
      }

      const message = (entry as { msg?: unknown }).msg;
      return typeof message === "string" && message.trim() ? message : null;
    })
    .filter((message): message is string => Boolean(message));

  return messages.length ? messages.join("; ") : null;
}
