import { lstat, realpath } from "node:fs/promises";
import { request, type IncomingMessage, type ServerResponse } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import type { Plugin } from "vite";
import { localRequestAllowed } from "./proxy.ts";
import { parseShareStatus, type ShareStatus } from "../src/features/apk-download/status.ts";

export function defaultStatusSocket() {
  return path.join(tmpdir(), `.avatar-apk-share-${process.getuid?.()}`, "status.sock");
}

export function statusRequestAllowed(req: Pick<IncomingMessage, "url" | "method" | "headers">) {
  return req.url === "/api/apk-share" && req.method === "GET" &&
    req.headers["x-avatar-apk-status"] === "1" &&
    (!req.headers["sec-fetch-site"] || req.headers["sec-fetch-site"] === "same-origin") &&
    localRequestAllowed(req.headers.host, req.headers.origin, "GET", String(req.headers["sec-fetch-site"] || ""));
}

// Nothing is read from a TCP status service. No API key/browser headers are forwarded.
export async function readShareStatus(socketPath: string, root: string): Promise<ShareStatus> {
  try {
    const parent = path.dirname(socketPath);
    const [dir, socket, canonicalParent] = await Promise.all([lstat(parent), lstat(socketPath), realpath(parent)]);
    const uid = process.getuid?.();
    if (!path.isAbsolute(socketPath) || canonicalParent !== parent ||
      canonicalParent === root || canonicalParent.startsWith(root + path.sep) ||
      !dir.isDirectory() || dir.uid !== uid || (dir.mode & 0o777) !== 0o700 ||
      !socket.isSocket() || socket.uid !== uid || (socket.mode & 0o777) !== 0o600)
      return { state: "unavailable" };
    const value = await new Promise<unknown>((resolve, reject) => {
      const req = request({ socketPath, path: "/status", method: "GET", timeout: 1000,
        headers: { Host: "localhost", "X-Avatar-Apk-Bridge": "1", Connection: "close" } }, (res) => {
        let size = 0;
        const chunks: Buffer[] = [];
        if (res.statusCode !== 200 || res.headers["content-type"] !== "application/json") {
          res.resume(); reject(new Error("Status unavailable")); return;
        }
        res.on("data", (chunk: Buffer) => {
          size += chunk.length;
          if (size > 8192) { res.destroy(); reject(new Error("Status too large")); }
          else chunks.push(chunk);
        });
        res.on("end", () => {
          try { resolve(JSON.parse(Buffer.concat(chunks).toString("utf8"))); } catch { reject(new Error("Invalid status")); }
        });
        res.on("error", reject);
      });
      req.on("timeout", () => req.destroy(new Error("Status timed out")));
      req.on("error", reject);
      req.end();
    });
    return parseShareStatus(value);
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    return { state: code === "ENOENT" || code === "ECONNREFUSED" ? "inactive" : "unavailable" };
  }
}

export function apkShareBridge(): Plugin {
  let root = "";
  const socketPath = process.env.AVATAR_APK_STATUS_SOCKET || defaultStatusSocket();
  return {
    name: "avatar-private-apk-status",
    configResolved(config) { root = path.resolve(config.root, ".."); },
    configureServer(server) {
      server.middlewares.use(async (req: IncomingMessage, res: ServerResponse, next) => {
        if (!req.url?.startsWith("/api/apk-share")) return next();
        res.setHeader("Cache-Control", "no-store");
        res.setHeader("Referrer-Policy", "no-referrer");
        res.setHeader("X-Content-Type-Options", "nosniff");
        res.setHeader("Content-Type", "application/json");
        if (!statusRequestAllowed(req)) {
          res.statusCode = 403; res.end(JSON.stringify({ state: "unavailable" })); return;
        }
        res.end(JSON.stringify(await readShareStatus(socketPath, root)));
      });
    },
  };
}
