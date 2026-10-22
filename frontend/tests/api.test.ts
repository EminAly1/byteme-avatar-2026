import { afterEach, expect, it, vi } from "vitest";
import { all, ApiError, newCommand, request, send } from "../src/lib/api";
afterEach(() => vi.unstubAllGlobals());
it("next_cursor bitene kadar API sayfalarını okur", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(
      Response.json({ items: [{ id: "a" }], next_cursor: "cursor2" }),
    )
    .mockResolvedValueOnce(
      Response.json({ items: [{ id: "b" }], next_cursor: null }),
    );
  vi.stubGlobal("fetch", fetch);
  expect(await all("/stocks?lot_id=x")).toEqual([{ id: "a" }, { id: "b" }]);
  expect(fetch.mock.calls[1][0]).toContain("lot_id=x&limit=100&cursor=cursor2");
});
it("tekrarlayan cursor ile eksik listeyi başarılı göstermez", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(Response.json({ items: [], next_cursor: "same" })),
      ),
  );
  await expect(all("/products")).rejects.toMatchObject({ code: "PAGINATION" });
});
it.each([401, 409, 422, 503])(
  "%s durumunu anlamlı hata olarak döndürür",
  async (status) => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          Response.json({ error: { code: "TEST" } }, { status }),
        ),
    );
    await expect(request("/products")).rejects.toBeInstanceOf(ApiError);
  },
);
it("ağ hatası sonrası aynı komut aynı UUID ve gövdeyle gider", async () => {
  const fetch = vi
    .fn()
    .mockRejectedValueOnce(new TypeError("offline"))
    .mockResolvedValueOnce(Response.json({ id: "ok" }));
  vi.stubGlobal("fetch", fetch);
  const command = newCommand("/receipts", {
    lines: [{ quantity: "100", total_cost: "970.00" }],
  });
  await expect(send(command)).rejects.toMatchObject({ uncertain: true });
  await send(command);
  expect(fetch.mock.calls[0][1].headers).toEqual(
    fetch.mock.calls[1][1].headers,
  );
  expect(fetch.mock.calls[0][1].body).toEqual(fetch.mock.calls[1][1].body);
  expect("X-API-Key" in fetch.mock.calls[1][1].headers).toBe(false);
});
