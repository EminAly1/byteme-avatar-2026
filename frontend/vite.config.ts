import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { LOCAL_ORIGIN, localApiGuard } from "./server/proxy.ts";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_API_PROXY_TARGET");
  const target =
    process.env.AVATAR_API_PROXY_TARGET ||
    env.VITE_API_PROXY_TARGET ||
    "http://127.0.0.1:8000";
  const url = new URL(target);
  if (
    url.protocol !== "http:" ||
    url.hostname !== "127.0.0.1" ||
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash
  ) {
    throw new Error("Yerel demo API hedefi http://127.0.0.1:<port> olmalıdır.");
  }
  return {
    plugins: [react(), tailwindcss(), localApiGuard()],
    server: {
      host: "127.0.0.1",
      port: 5173,
      strictPort: true,
      cors: { origin: LOCAL_ORIGIN },
      fs: {
        deny: [
          ".env",
          ".env.*",
          "**/.env*",
          "**/*.{crt,pem,key}",
          "**/.git/**",
        ],
      },
      proxy: {
        "/api": {
          target,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
          configure(proxy) {
            proxy.on("proxyReq", (request) => {
              request.removeHeader("X-API-Key");
              // This value exists only in the Node/Vite process; never define it for React.
              if (process.env.AVATAR_API_KEY)
                request.setHeader("X-API-Key", process.env.AVATAR_API_KEY);
            });
          },
        },
      },
    },
    preview: { host: "127.0.0.1", port: 4173, strictPort: true, proxy: {} },
  };
});
