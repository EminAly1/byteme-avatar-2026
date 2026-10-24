import type { IncomingMessage, ServerResponse } from "node:http";
import type { Plugin } from "vite";

export const LOCAL_ORIGIN = "http://127.0.0.1:5173";

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

export function localApiGuard(): Plugin {
  return {
    name: "avatar-local-api-guard",
    configResolved(config) {
      if (config.server.host !== "127.0.0.1")
        throw new Error("API proxy yalnızca 127.0.0.1 üzerinde çalışabilir.");
    },
    configureServer(server) {
      server.middlewares.use(
        (req: IncomingMessage, res: ServerResponse, next) => {
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
