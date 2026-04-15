const baseUrl =
  process.env.FASTAPI_BASE_URL?.trim() ||
  process.env.NEXT_PUBLIC_FASTAPI_BASE_URL?.trim() ||
  "http://localhost:8000";

async function main() {
  const healthResponse = await fetchJson(`${baseUrl}/health`);
  assert(
    healthResponse.response.ok,
    `health returned ${healthResponse.response.status}: ${JSON.stringify(healthResponse.body)}`,
  );
  assert(
    healthResponse.body.status === "ok",
    `Expected health status to be "ok", got ${JSON.stringify(healthResponse.body)}`,
  );

  const voiceResponse = await fetchJson(`${baseUrl}/voice-parse`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      transcript: "Union Square to Lincoln Center",
    }),
  });
  assert(
    voiceResponse.response.ok,
    `voice-parse returned ${voiceResponse.response.status}: ${JSON.stringify(voiceResponse.body)}`,
  );

  const routeResponse = await fetchJson(`${baseUrl}/route-analysis`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      origin: {
        address: "Start",
        location: { lat: 40.74, lng: -73.984 },
      },
      destination: {
        address: "End",
        location: { lat: 40.788, lng: -73.984 },
      },
      profile: {
        triggers: [],
        sensitivity: "medium",
        knowsTreeTriggers: false,
      },
    }),
  });
  assert(
    routeResponse.response.ok,
    `route-analysis returned ${routeResponse.response.status}: ${JSON.stringify(routeResponse.body)}`,
  );

  console.log("FastAPI is healthy and serving voice-parse and route-analysis directly.");
}

async function fetchJson(url, init) {
  const response = await fetch(url, init);
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  return { response, body };
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(message);
  process.exitCode = 1;
});
