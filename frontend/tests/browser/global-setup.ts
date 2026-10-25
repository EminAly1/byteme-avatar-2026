import type { FullConfig } from "@playwright/test";
export default async function setup(_: FullConfig) {
  if (
    !process.env.AVATAR_E2E_DATABASE?.endsWith("_test") ||
    !process.env.AVATAR_API_KEY
  )
    throw new Error(
      "E2E writes/recalls require an isolated AVATAR_E2E_DATABASE ending in _test and server-side AVATAR_API_KEY. Run backend with the same MYSQL_DATABASE; never use business/shared demo data.",
    );
  const url = new URL(
    process.env.AVATAR_E2E_API_URL || "http://127.0.0.1:8000",
  );
  if (url.hostname !== "127.0.0.1")
    throw new Error("E2E backend must be the dedicated local instance.");
}
