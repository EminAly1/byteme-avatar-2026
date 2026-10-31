import { expect, it } from "vitest";
import { chmod, mkdir, mkdtemp, rm } from "node:fs/promises";
import { createServer, type IncomingMessage } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import { randomBytes } from "node:crypto";
import { readShareStatus, statusRequestAllowed } from "../server/apk-share";
import { parseShareStatus } from "../src/features/apk-download/status";

const capability = () => randomBytes(32).toString("base64url");
function valid() {
  return { state: "active", url: `http://192.168.1.20:8765/download/${capability()}`, expiresAt: Date.now() + 180000,
    version: "0.1.0-preview.2", bytes: 100, sha256: "a".repeat(64) };
}
it("yalnız açık özel IPv4, sınırlı ömür ve doğrulanmış APK metadata kabul eder", () => {
  expect(parseShareStatus(valid()).state).toBe("active");
  for (const host of ["localhost", "127.0.0.1", "0.0.0.0", "8.8.8.8", "192.168.1.20.evil.test", "[::1]"]) {
    expect(() => parseShareStatus({ ...valid(), url: `http://${host}:8765/download/${capability()}` })).toThrow();
  }
  for (const patch of [{ bytes: 0 }, { bytes: 129 * 1024 * 1024 }, { sha256: "bad" }, { version: "<script>" },
    { expiresAt: Date.now() + 700000 }, { url: valid().url + "?file=.env" }, { url: valid().url + "#extra" }])
    expect(() => parseShareStatus({ ...valid(), ...patch })).toThrow();
  expect(parseShareStatus({ ...valid(), expiresAt: Date.now() - 1 })).toEqual({ state: "expired" });
  expect(parseShareStatus({ ...valid(), state: "used" })).toEqual({ state: "used" }); // Strip capability.
});
it("durum endpoint'i yalnız aynı origin GET ve özel başlığı kabul eder", () => {
  const req = { url: "/api/apk-share", method: "GET", headers: { host: "127.0.0.1:5173", "x-avatar-apk-status": "1", "sec-fetch-site": "same-origin" } };
  expect(statusRequestAllowed(req)).toBe(true);
  for (const patch of [{ method: "POST" }, { url: "/api/apk-share?file=.env" }, { url: "/api/apk-share/" },
    { headers: { ...req.headers, origin: "http://evil.test" } }, { headers: { ...req.headers, host: "192.168.1.20:5173" } },
    { headers: { ...req.headers, "sec-fetch-site": "same-site" } }, { headers: { host: "127.0.0.1:5173" } }])
    expect(statusRequestAllowed({ ...req, ...patch })).toBe(false);
});
it("yalnız 0700/0600 sahipli Unix soketinden okur, hata ve kapanışta token döndürmez", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), ".avatar-apk-share-test-"));
  const socketPath = path.join(dir, "status.sock");
  let reply: unknown = valid();
  let headersSafe = false;
  const server = createServer((req, res) => {
    headersSafe = req.url === "/status" && req.headers.host === "localhost" && req.headers["x-avatar-apk-bridge"] === "1" && !req.headers["x-api-key"];
    res.setHeader("Content-Type", "application/json"); res.end(JSON.stringify(reply));
  });
  try {
    await chmod(dir, 0o700);
    await new Promise<void>((resolve) => server.listen(socketPath, resolve)); await chmod(socketPath, 0o600);
    expect((await readShareStatus(socketPath, "/unrelated-repo")).state).toBe("active");
    expect(headersSafe).toBe(true);
    expect(await readShareStatus(socketPath, dir)).toEqual({ state: "unavailable" });
    reply = { ...valid(), url: "http://127.0.0.1:8765/download/" + capability() };
    expect(await readShareStatus(socketPath, "/unrelated-repo")).toEqual({ state: "unavailable" });
    reply = "x".repeat(9000);
    expect(await readShareStatus(socketPath, "/unrelated-repo")).toEqual({ state: "unavailable" });
    await chmod(socketPath, 0o666);
    expect(await readShareStatus(socketPath, "/unrelated-repo")).toEqual({ state: "unavailable" });
    await chmod(socketPath, 0o600); await chmod(dir, 0o755);
    expect(await readShareStatus(socketPath, "/unrelated-repo")).toEqual({ state: "unavailable" });
  } finally {
    await new Promise<void>((resolve) => server.close(() => resolve())); await rm(dir, { recursive: true, force: true });
  }
  expect(await readShareStatus(socketPath, "/unrelated-repo")).toEqual({ state: "inactive" });
});
