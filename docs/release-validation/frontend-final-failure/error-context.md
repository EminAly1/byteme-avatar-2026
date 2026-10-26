# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: integration-v2.spec.ts >> lotlu UI satış → bağlı sevkiyat aynı hareket; bağımsız sevkiyat yeni çıkış
- Location: tests/browser/integration-v2.spec.ts:185:1

# Error details

```
TimeoutError: locator.click: Timeout 10000ms exceeded.
Call log:
  - waiting for getByRole('row').filter({ hasText: 'V2-31810223 Market' }).getByRole('button', { name: 'Sevkiyatı aç', exact: true })
    - locator resolved to <button class="text-button">Sevkiyatı aç</button>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <td class="">…</td> from <dialog open="" class="detail-drawer" aria-labelledby="_r_a_">…</dialog> subtree intercepts pointer events
    - retrying click action
    - waiting 20ms
    - waiting for element to be visible, enabled and stable
    - element is visible, enabled and stable
    - scrolling into view if needed
    - done scrolling
    - <td class="">…</td> from <dialog open="" class="detail-drawer" aria-labelledby="_r_a_">…</dialog> subtree intercepts pointer events
  2 × retrying click action
      - waiting 100ms
      - waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <dialog open="" class="detail-drawer" aria-labelledby="_r_a_">…</dialog> intercepts pointer events
  4 × retrying click action
      - waiting 500ms
      - waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <td class="">…</td> from <dialog open="" class="detail-drawer" aria-labelledby="_r_a_">…</dialog> subtree intercepts pointer events
    - retrying click action
      - waiting 500ms
      - waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <td class="">…</td> from <dialog open="" class="detail-drawer" aria-labelledby="_r_a_">…</dialog> subtree intercepts pointer events
    - retrying click action
      - waiting 500ms
      - waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <dialog open="" class="detail-drawer" aria-labelledby="_r_a_">…</dialog> intercepts pointer events
    - retrying click action
      - waiting 500ms
      - waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <dialog open="" class="detail-drawer" aria-labelledby="_r_a_">…</dialog> intercepts pointer events
  2 × retrying click action
      - waiting 500ms
      - waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <td class="">…</td> from <dialog open="" class="detail-drawer" aria-labelledby="_r_a_">…</dialog> subtree intercepts pointer events
  - retrying click action
    - waiting 500ms

```

# Test source

```ts
  130 |       .click();
  131 |     await page.getByLabel("Fark kg 1", { exact: true }).fill("3");
  132 |     await page
  133 |       .getByRole("button", { name: "Kesimi kapat", exact: true })
  134 |       .click();
  135 |     await expect(
  136 |       page.getByLabel("Fark nedeni 1", { exact: true }),
  137 |     ).toHaveAttribute("aria-invalid", "true");
  138 |     await page
  139 |       .getByLabel("Fark nedeni 1", { exact: true })
  140 |       .fill("KURGUSAL E2E test ölçümü; gerçek işletme verisi değildir.");
  141 |     if (index === 0) {
  142 |       await page.route("**/api/v1/cuttings/*/post", async (route) => {
  143 |         const body = route.request().postDataJSON();
  144 |         body.differences[0].quantity = "2";
  145 |         await route.continue({ postData: JSON.stringify(body) });
  146 |       });
  147 |       await confirm(page, "Kesimi kapat");
  148 |       await expect(page.getByRole("alert")).toContainText("dengelenmiyor");
  149 |       expect(await stock(request, s.lots[index], s.location.id)).toBe(
  150 |         "25.000000",
  151 |       );
  152 |       await page.unroute("**/api/v1/cuttings/*/post");
  153 |     }
  154 |     const closedResponse = page.waitForResponse(
  155 |       (r) => r.request().method() === "POST" && r.url().endsWith("/post"),
  156 |     );
  157 |     await confirm(page, "Kesimi kapat");
  158 |     const closed = (await (await closedResponse).json()) as Cutting;
  159 |     expect(closed.total_cost).toBe("287.500000");
  160 |     expect(closed.outputs).toHaveLength(5);
  161 |     results.push(closed);
  162 |     await expect(
  163 |       page.getByRole("heading", {
  164 |         name: "Parça lotları ve maliyetler",
  165 |         exact: true,
  166 |       }),
  167 |     ).toBeVisible();
  168 |     expect(await stock(request, s.lots[index], s.location.id)).toBe("0.000000");
  169 |   }
  170 |   expect(results[0].outputs.map((o) => o.allocated_cost)).not.toEqual(
  171 |     results[1].outputs.map((o) => o.allocated_cost),
  172 |   );
  173 |   await capture(page, "cutting-desktop");
  174 |   await page.setViewportSize({ width: 390, height: 844 });
  175 |   await capture(page, "cutting-mobile");
  176 |   evidence.push({
  177 |     scenario: "two independent 25 kg cuts",
  178 |     source_lots: s.lots,
  179 |     cutting_ids: results.map((r) => r.id),
  180 |     cost_each: "287.500000",
  181 |     backend_422_verified: true,
  182 |   });
  183 | });
  184 |
  185 | test("lotlu UI satış → bağlı sevkiyat aynı hareket; bağımsız sevkiyat yeni çıkış", async ({
  186 |   page,
  187 |   request,
  188 | }) => {
  189 |   const s = await seedTrade(request);
  190 |   await page.goto("/satislar");
  191 |   await page.getByRole("button", { name: "Yeni satış", exact: true }).click();
  192 |   await page.getByLabel("Müşteri", { exact: true }).selectOption(s.customer.id);
  193 |   await page
  194 |     .getByLabel("Lot / konum 1", { exact: true })
  195 |     .selectOption(s.lot + "|" + s.location.id);
  196 |   await page.getByLabel("Miktar 1", { exact: true }).fill("1");
  197 |   await page.getByLabel("Birim fiyat 1 (EUR)", { exact: true }).fill("25,00");
  198 |   const saleResponse = page.waitForResponse(
  199 |     (r) => r.request().method() === "POST" && r.url().endsWith("/sales"),
  200 |   );
  201 |   await confirm(page, "Satışı gözden geçir");
  202 |   const sale = (await (await saleResponse).json()) as SaleDetail;
  203 |   await expect(page).toHaveURL("/satislar/" + sale.id);
  204 |   expect(await stock(request, s.lot, s.location.id)).toBe("9.000000");
  205 |   await page.locator('summary').filter({hasText:'Stok hareketi'}).click();
  206 |   await expect(
  207 |     page.getByText(sale.lines[0].stock_movement_id, { exact: true }),
  208 |   ).toBeVisible();
  209 |   await page
  210 |     .getByRole("link", {
  211 |       name: "Bu satışa bağlı sevkiyat oluştur",
  212 |       exact: true,
  213 |     })
  214 |     .click();
  215 |   await expect(
  216 |     page.getByText(/Bağlı sevkiyat satışın stok hareketini paylaşır/),
  217 |   ).toBeVisible();
  218 |   const shipResponse = page.waitForResponse(
  219 |     (r) => r.request().method() === "POST" && r.url().endsWith("/shipments"),
  220 |   );
  221 |   await confirm(page, "Bağlı sevkiyatı gözden geçir");
  222 |   const shipment = (await (await shipResponse).json()) as ShipmentDetail;
  223 |   expect(shipment.lines[0].stock_movement_id).toBe(
  224 |     sale.lines[0].stock_movement_id,
  225 |   );
  226 |   expect(await stock(request, s.lot, s.location.id)).toBe("9.000000");
  227 |   await expect(page.getByRole("dialog")).toBeVisible();
  228 |   await page.keyboard.press('Escape');
  229 |   const openShipment = page.getByRole('row').filter({hasText:s.customer.name}).getByRole('button',{name:'Sevkiyatı aç',exact:true});
> 230 |   await openShipment.click();
      |                      ^ TimeoutError: locator.click: Timeout 10000ms exceeded.
  231 |   await expect(page.getByRole('button',{name:'Ayrıntıyı kapat',exact:true})).toBeFocused();
  232 |   await page.keyboard.press('Shift+Tab');
  233 |   await expect(page.getByRole('dialog').locator('summary').filter({hasText:'Stok hareketi'}).last()).toBeFocused();
  234 |   await page.keyboard.press('Tab');
  235 |   await expect(page.getByRole('button',{name:'Ayrıntıyı kapat',exact:true})).toBeFocused();
  236 |   await page.keyboard.press('Escape');
  237 |   await expect(openShipment).toBeFocused();
  238 |   await page
  239 |     .getByRole("button", { name: "Bağımsız sevkiyat", exact: true })
  240 |     .click();
  241 |   await page.getByLabel("Müşteri", { exact: true }).selectOption(s.customer.id);
  242 |   await page
  243 |     .getByLabel("Lot / konum 1", { exact: true })
  244 |     .selectOption(s.lot + "|" + s.location.id);
  245 |   await page.getByLabel("Miktar 1", { exact: true }).fill("2");
  246 |   await confirm(page, "Bağımsız sevkiyatı gözden geçir");
  247 |   await expect
  248 |     .poll(() => stock(request, s.lot, s.location.id))
  249 |     .toBe("7.000000");
  250 |   evidence.push({
  251 |     scenario: "sale + linked + independent shipment",
  252 |     sale_id: sale.id,
  253 |     shipment_id: shipment.id,
  254 |     shared_movement: sale.lines[0].stock_movement_id,
  255 |     stock: "10→9→9→7",
  256 |   });
  257 | });
  258 |
  259 | test("gerçek ileri/geri izleme ve ET recall → Market A/B/C 30/25/30; onay şart", async ({
  260 |   page,
  261 |   request,
  262 | }) => {
  263 |   const lots = await apiAll<Lot>(request, "/lots");
  264 |   const root = lots.find((l) => l.external_code === "ET-2026-001")!,
  265 |     finished = lots.find((l) => l.external_code === "SUC-2026-045")!;
  266 |   expect(root).toBeTruthy();
  267 |   await page.goto("/izlenebilirlik?lot=" + root.id);
  268 |   await expect(
  269 |     page.getByRole("heading", {
  270 |       name: "Kaynak lotun ileri kayıt zinciri",
  271 |       exact: true,
  272 |     }),
  273 |   ).toBeVisible();
  274 |   await expect(page.getByText("85 paket", { exact: true })).toBeVisible();
  275 |   await capture(page, "trace-desktop");
  276 |   await page
  277 |     .getByLabel("İzlenecek lot", { exact: true })
  278 |     .selectOption(finished.id);
  279 |   await page
  280 |     .getByLabel("İzleme yönü", { exact: true })
  281 |     .selectOption("backward");
  282 |   await expect(
  283 |     page.getByRole("heading", {
  284 |       name: "Kaynaklara doğru kayıt zinciri",
  285 |       exact: true,
  286 |     }),
  287 |   ).toBeVisible();
  288 |   await expect(
  289 |     page.getByText("ET-2026-001", { exact: true }).first(),
  290 |   ).toBeVisible();
  291 |   await page.goto("/geri-cagirma");
  292 |   await page
  293 |     .getByLabel("Sorunlu kaynak lot", { exact: true })
  294 |     .selectOption(root.id);
  295 |   await expect(
  296 |     page.getByText(/henüz kesinleşmiş recall sonucu değildir/),
  297 |   ).toBeVisible();
  298 |   let calls = 0;
  299 |   page.on("request", (r) => {
  300 |     if (r.method() === "POST" && r.url().endsWith("/recalls")) calls++;
  301 |   });
  302 |   await page
  303 |     .getByLabel("Geri çağırma nedeni", { exact: true })
  304 |     .fill("KURGUSAL E2E kalite kontrolü");
  305 |   await page
  306 |     .getByRole("button", { name: "Geri çağırmayı gözden geçir", exact: true })
  307 |     .click();
  308 |   await expect(page.getByRole("dialog")).toBeVisible();
  309 |   expect(calls).toBe(0);
  310 |   await page.keyboard.press("Escape");
  311 |   await expect(
  312 |     page.getByRole("button", {
  313 |       name: "Geri çağırmayı gözden geçir",
  314 |       exact: true,
  315 |     }),
  316 |   ).toBeFocused();
  317 |   expect(calls).toBe(0);
  318 |   const response = page.waitForResponse(
  319 |     (r) => r.request().method() === "POST" && r.url().endsWith("/recalls"),
  320 |   );
  321 |   await confirm(page, "Geri çağırmayı gözden geçir");
  322 |   const recall = (await (await response).json()) as Recall;
  323 |   await expect(page).toHaveURL("/geri-cagirma/" + recall.id);
  324 |   await expect(page.getByText("GERİ ÇAĞIRMA AKTİF")).toBeVisible();
  325 |   expect(recall.report.buyers).toHaveLength(3);
  326 |   expect(recall.report.total_shipped_quantities[0].quantity).toBe("85.000000");
  327 |   expect(
  328 |     recall.report.buyers
  329 |       .flatMap((b) => b.quantities.map((q) => q.shipped_quantity))
  330 |       .sort(),
```
