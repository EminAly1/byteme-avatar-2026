import type { IncomingMessage, ServerResponse } from "node:http";
import type { Plugin } from "vite";

export const LOCAL_ORIGIN = "http://127.0.0.1:5173";

export function secretPathBlocked(url: string) {
  let path = url.split("?")[0];
  try {
    for (let i = 0; i < 2; i++) path = decodeURIComponent(path);
  } catch {
    return true;
  }
  return /(?:^|[\\/])(?:\.env[^\\/]*|\.git)(?:[\\/]|$)|\.(?:crt|pem|key)$/i.test(path);
}

// Container bind is an explicit server-side deployment choice. Browser Host /
// Origin and the upstream's literal-loopback allowlist stay identical.
export function demoBindHost(containerMode?: string) {
  if (containerMode !== undefined && containerMode !== "1")
    throw new Error("AVATAR_DEMO_CONTAINER_BIND yalnızca 1 olabilir.");
  return containerMode === "1" ? "0.0.0.0" : "127.0.0.1";
}

export function localRequestAllowed(
  host: string | undefined,
  origin: string | undefined,
  method: string,
  site?: string,
) {
  if (host !== "127.0.0.1:5173" || site === "cross-site") return false;
  if (origin && origin !== LOCAL_ORIGIN) return false;
  return ["GET", "HEAD"].includes(method) || origin === LOCAL_ORIGIN;
}

export function localApiGuard(bindHost = "127.0.0.1"): Plugin {
  return {
    name: "avatar-local-api-guard",
    configResolved(config) {
      if (config.server.host !== bindHost)
        throw new Error("API proxy bind adresi güvenilir demo yapılandırmasıyla eşleşmelidir.");
    },
    configureServer(server) {
      server.middlewares.use(
        (req: IncomingMessage, res: ServerResponse, next) => {
          // Deny before Vite's SPA fallback, even when the file is absent in
          // this container. Never serve an HTML success for a secret path.
          if (secretPathBlocked(req.url || "")) {
            res.writeHead(403, { "Content-Type": "text/plain" });
            res.end("Dosya erişimi reddedildi.");
            return;
          }
          if (!req.url?.startsWith("/api")) return next();
          const origin =
            typeof req.headers.origin === "string"
              ? req.headers.origin
              : undefined;
          if (
            !localRequestAllowed(
              req.headers.host,
              origin,
              req.method || "GET",
              String(req.headers["sec-fetch-site"] || ""),
            )
          ) {
            res.writeHead(403, { "Content-Type": "application/json" });
            res.end(
              JSON.stringify({
                error: {
                  code: "LOCAL_ONLY",
                  message:
                    "Bu demo yalnızca aynı yerel origin üzerinden kullanılabilir.",
                },
              }),
            );
            return;
          }
          if (req.url.startsWith("/api/v1") && !process.env.AVATAR_API_KEY) {
            res.writeHead(503, { "Content-Type": "application/json" });
            res.end(
              JSON.stringify({
                error: {
                  code: "PROXY_KEY_MISSING",
                  message: "Yerel API bağlantısı sunucuda yapılandırılmamış.",
                },
              }),
            );
            return;
          }
          next();
        },
      );
    },
  };
}
