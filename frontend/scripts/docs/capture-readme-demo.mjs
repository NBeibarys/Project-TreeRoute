import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const DEMO_URL = process.env.TREEROUTE_DEMO_URL ?? "https://treeroute-501252220143.us-central1.run.app/";
const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(SCRIPT_DIR, "../../..");
const OUT_DIR = path.join(ROOT, "docs", "media", "frames");
const USER_DATA_DIR = path.join(ROOT, ".chrome-readme-demo");
const DEBUG_PORT = 9222;
const WINDOW_SIZE = { width: 1440, height: 1200 };

const chromePath = resolveChromePath();

async function main() {
  await rm(OUT_DIR, { recursive: true, force: true });
  await mkdir(OUT_DIR, { recursive: true });
  await rm(USER_DATA_DIR, { recursive: true, force: true });
  await mkdir(USER_DATA_DIR, { recursive: true });

  const chrome = spawn(
    chromePath,
    [
      "--headless=new",
      "--disable-gpu",
      "--disable-crash-reporter",
      "--no-first-run",
      `--remote-debugging-port=${DEBUG_PORT}`,
      `--user-data-dir=${USER_DATA_DIR}`,
      `--window-size=${WINDOW_SIZE.width},${WINDOW_SIZE.height}`,
      "about:blank",
    ],
    {
      stdio: "ignore",
      windowsHide: true,
    },
  );

  try {
    const wsUrl = await waitForTargetWebSocketUrl();
    const client = await createCdpClient(wsUrl);

    await client.send("Page.enable");
    await client.send("Runtime.enable");
    await client.send("Emulation.setDeviceMetricsOverride", {
      width: WINDOW_SIZE.width,
      height: WINDOW_SIZE.height,
      deviceScaleFactor: 1,
      mobile: false,
    });

    await client.navigate(DEMO_URL);
    await client.wait(2000);
    await client.capture(path.join(OUT_DIR, "01-home.png"));

    await client.evaluate(`
      (() => {
        const setValue = (selector, value) => {
          const input = document.querySelector(selector);
          if (!input) return false;
          const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
          descriptor?.set?.call(input, value);
          input.dispatchEvent(new Event("input", { bubbles: true }));
          input.dispatchEvent(new Event("change", { bubbles: true }));
          return true;
        };

        setValue('input[placeholder="Starting location..."]', 'Washington Square Park, New York, NY');
        setValue('input[placeholder="Destination..."]', 'Lincoln Center, New York, NY');
      })();
    `);
    await client.wait(900);
    await client.capture(path.join(OUT_DIR, "02-home-filled.png"));

    await client.evaluate(`
      localStorage.setItem(
        "treeroute-route-draft",
        JSON.stringify({
          origin: { address: "Washington Square Park, New York, NY" },
          destination: { address: "Lincoln Center, New York, NY" }
        })
      );
      localStorage.setItem(
        "pollen-safe-profile",
        JSON.stringify({
          name: "Daniyar",
          email: "daniyar@example.com",
          triggers: ["oak", "birch", "maple"],
          sensitivity: "high",
          notes: "",
          registrationComplete: false,
          knowsTreeTriggers: true
        })
      );
    `);
    await client.navigate(new URL("/register", DEMO_URL).toString());
    await client.wait(2200);
    await client.capture(path.join(OUT_DIR, "03-register.png"));

    await client.evaluate(`
      localStorage.setItem(
        "pollen-safe-profile",
        JSON.stringify({
          name: "Daniyar",
          email: "daniyar@example.com",
          triggers: ["oak", "birch", "maple"],
          sensitivity: "high",
          notes: "",
          registrationComplete: true,
          knowsTreeTriggers: true
        })
      );
    `);
    await client.navigate(new URL("/planner", DEMO_URL).toString());
    await client.wait(2500);
    await client.capture(path.join(OUT_DIR, "04-planner-prefilled.png"));

    await client.evaluate(`
      (() => {
        const button = document.querySelector('button[type="submit"]');
        button?.click();
      })();
    `);
    await client.waitFor(
      () => client.evaluate("document.querySelectorAll('.route-card').length"),
      (value) => Number(value) > 0,
      30000,
      750,
    );
    await client.wait(1500);
    await client.capture(path.join(OUT_DIR, "05-planner-results.png"));

    await client.close();
  } finally {
    chrome.kill("SIGKILL");
  }
}

function resolveChromePath() {
  const candidates = [
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ];

  const found = candidates.find((candidate) => existsSync(candidate));
  if (!found) {
    throw new Error("Chrome or Edge was not found on this machine.");
  }

  return found;
}

async function waitForTargetWebSocketUrl() {
  const endpoint = `http://127.0.0.1:${DEBUG_PORT}/json/list`;

  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await fetch(endpoint);
      const targets = await response.json();
      const pageTarget = targets.find((target) => target.type === "page" && target.webSocketDebuggerUrl);
      if (pageTarget?.webSocketDebuggerUrl) {
        return pageTarget.webSocketDebuggerUrl;
      }
    } catch {
      // Chrome may not be ready yet.
    }

    await delay(250);
  }

  throw new Error("Unable to connect to Chrome DevTools Protocol.");
}

async function createCdpClient(wsUrl) {
  const socket = new WebSocket(wsUrl);
  const pending = new Map();
  let commandId = 0;
  let loadResolve = null;

  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(String(event.data));

    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) {
        reject(new Error(message.error.message));
      } else {
        resolve(message.result);
      }
      return;
    }

    if (message.method === "Page.loadEventFired" && loadResolve) {
      const done = loadResolve;
      loadResolve = null;
      done();
    }
  });

  return {
    async send(method, params = {}) {
      const id = ++commandId;
      const payload = JSON.stringify({ id, method, params });

      const result = new Promise((resolve, reject) => {
        pending.set(id, { resolve, reject });
      });

      socket.send(payload);
      return result;
    },

    async navigate(url) {
      const loadPromise = new Promise((resolve) => {
        loadResolve = resolve;
      });

      await this.send("Page.navigate", { url });
      await loadPromise;
      await this.wait(800);
    },

    async evaluate(expression) {
      const result = await this.send("Runtime.evaluate", {
        expression,
        awaitPromise: true,
        returnByValue: true,
      });
      return result.result?.value;
    },

    async capture(filePath) {
      const screenshot = await this.send("Page.captureScreenshot", {
        format: "png",
        fromSurface: true,
      });
      await writeFile(filePath, Buffer.from(screenshot.data, "base64"));
    },

    wait(ms) {
      return delay(ms);
    },

    async waitFor(task, predicate, timeoutMs, intervalMs) {
      const start = Date.now();
      while (Date.now() - start < timeoutMs) {
        const value = await task();
        if (predicate(value)) {
          return value;
        }
        await delay(intervalMs);
      }

      throw new Error("Timed out waiting for page state.");
    },

    async close() {
      socket.close();
      await delay(200);
    },
  };
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
