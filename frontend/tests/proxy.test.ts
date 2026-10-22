import { expect, it } from "vitest";
import { localRequestAllowed, LOCAL_ORIGIN } from "../server/proxy";
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
