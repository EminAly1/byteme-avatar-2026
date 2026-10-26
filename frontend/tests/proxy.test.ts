import { expect, it } from "vitest";
import { localRequestAllowed, LOCAL_ORIGIN, demoBindHost, localApiGuard, secretPathBlocked } from "../server/proxy";
it("yalnızca beklenen loopback host ve origin ile API erişimini kabul eder", () => {
  expect(
    localRequestAllowed("127.0.0.1:5173", LOCAL_ORIGIN, "POST", "same-origin"),
  ).toBe(true);
  expect(localRequestAllowed("127.0.0.1:5173", undefined, "GET")).toBe(true);
  expect(
    localRequestAllowed("127.0.0.1:5173", "https://evil.example", "POST"),
  ).toBe(false);
  expect(localRequestAllowed("127.0.0.1:5173", undefined, "POST")).toBe(false);
  expect(localRequestAllowed("evil.example", LOCAL_ORIGIN, "GET")).toBe(false);
  expect(
    localRequestAllowed("127.0.0.1:5173", LOCAL_ORIGIN, "POST", "cross-site"),
  ).toBe(false);
});
it("gizli yollar dosya varlığından bağımsız ve kodlanmış biçimleriyle reddedilir", () => {
  for (const path of ["/.env", "/@fs/workspace/backend/.env.runtime", "/app/.env.local?raw", "/%252eenv", "/.git/config", "/cert/private.key", "/%ZZ"])
    expect(secretPathBlocked(path)).toBe(true);
  for (const path of ["/", "/src/main.tsx", "/api/v1/products", "/@vite/client", "/.github/workflows"])
    expect(secretPathBlocked(path)).toBe(false);
});
it("container bind opt-in'i Host/Origin denetimini ve varsayılan kapalı sınırı değiştirmez", () => {
  expect(demoBindHost()).toBe("127.0.0.1");
  expect(demoBindHost("1")).toBe("0.0.0.0");
  expect(() => demoBindHost("0")).toThrow();
  const hook = localApiGuard(demoBindHost("1")).configResolved as (config: unknown) => void;
  expect(() => hook({server:{host:"0.0.0.0"}})).not.toThrow();
  expect(() => hook({server:{host:"backend"}})).toThrow();
  expect(localRequestAllowed("backend:5173", LOCAL_ORIGIN, "POST")).toBe(false);
  expect(localRequestAllowed("127.0.0.1:5173", "http://backend:5173", "POST")).toBe(false);
});
