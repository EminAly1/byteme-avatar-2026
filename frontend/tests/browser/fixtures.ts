import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
import type {
  Product,
  Party,
  Location,
  ReceiptDetail,
  Operation,
  Stock,
} from "../../src/lib/types";
import type { Recipe, Cutting, SaleDetail } from "../../src/lib/modules";
const base = process.env.AVATAR_E2E_API_URL || "http://127.0.0.1:8000";
export async function api<T>(
  r: APIRequestContext,
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await r.fetch(base + "/v1" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "X-API-Key": process.env.AVATAR_API_KEY || "",
      ...(body !== undefined ? { "Idempotency-Key": randomUUID() } : {}),
    },
    ...(body !== undefined ? { data: body } : {}),
  });
  expect(response.ok(), `Real API ${path}: ${response.status()}`).toBe(true);
  return response.json();
}
export const prefix = () => "V2-" + randomUUID().slice(0, 8);
export async function confirm(page: Page, label: string) {
  await page.getByRole("button", { name: label, exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByRole("button", { name: "Onayla ve kaydet", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
}
export async function seedTrade(r: APIRequestContext, expires_at?: string) {
  const p = prefix(),
    supplier = await api<Party>(r, "/parties", {
      name: p + " Tedarikçi",
      roles: ["supplier"],
    }),
    customer = await api<Party>(r, "/parties", {
      name: p + " Market",
      roles: ["customer"],
      contact: "KURGUSAL E2E müşteri",
    }),
    location = await api<Location>(r, "/locations", { name: p + " Depo" }),
    product = await api<Product>(r, "/products", {
      sku: p + "-FOOD",
      name: p + " Gıda",
      type: "finished",
      base_unit: "kg",
    }),
    receipt = await api<ReceiptDetail>(r, "/receipts", {
      supplier_id: supplier.id,
      location_id: location.id,
      lines: [
        {
          product_id: product.id,
          external_lot_code: p + "-LOT",
          quantity: "10",
          total_cost: "100.00",
          ...(expires_at ? { expires_at } : {}),
        },
      ],
    });
  return {
    p,
    supplier,
    customer,
    location,
    product,
    lot: receipt.lines[0].lot_id,
  };
}
export async function seedLamb(r: APIRequestContext) {
  const p = prefix(),
    supplier = await api<Party>(r, "/parties", {
      name: p + " Kurgusal kuzu tedarikçisi",
      roles: ["supplier"],
    }),
    location = await api<Location>(r, "/locations", { name: p + " Kesimhane" }),
    source = await api<Product>(r, "/products", {
      sku: p + "-LAMB",
      name: p + " Kuzu",
      type: "raw",
      base_unit: "kg",
      species: "Kuzu",
    });
  const specs = [
    ["leg", "But", "6", "20.00"],
    ["shoulder", "Omuz", "4", "14.00"],
    ["back", "Sırt", "4", "24.00"],
    ["rib", "Kaburga", "5", "12.00"],
    ["mince", "Kıyma", "3", "10.00"],
  ];
  const parts = [];
  for (const [key, name, weight, reference] of specs) {
    const product = await api<Product>(r, "/products", {
      sku: p + "-" + key,
      name: p + " " + name,
      type: "finished",
      base_unit: "kg",
    });
    parts.push({ key, name, weight, reference, product });
  }
  const lots = [];
  for (let i = 0; i < 2; i++) {
    const receipt = await api<ReceiptDetail>(r, "/receipts", {
      supplier_id: supplier.id,
      location_id: location.id,
      lines: [
        {
          product_id: source.id,
          external_lot_code: p + "-LAMB-" + i,
          quantity: "25",
          unit_price: "11.50",
          total_cost: "287.50",
        },
      ],
    });
    lots.push(receipt.lines[0].lot_id);
  }
  return { p, supplier, location, source, parts, lots };
}
export async function seedRecipe(
  r: APIRequestContext,
  s: Awaited<ReturnType<typeof seedLamb>>,
) {
  return api<Recipe>(r, "/recipes", {
    code: s.p + "-KEY",
    version: 1,
    species: "Kuzu",
    input_product_id: s.source.id,
    allocation_method: "quantity",
    lines: s.parts.map((p) => ({ product_id: p.product.id })),
  });
}
export async function closeCutting(
  r: APIRequestContext,
  s: Awaited<ReturnType<typeof seedLamb>>,
  c: Operation,
) {
  return api<Cutting>(r, "/cuttings/" + c.id + "/post", {
    consumed_inputs: [
      { lot_id: s.lots[0], location_id: s.location.id, quantity: "25" },
    ],
    output_location_id: s.location.id,
    outputs: s.parts.map((p) => ({
      product_id: p.product.id,
      lot_code: s.p + "-PART-" + p.key,
      quantity: p.weight,
    })),
    differences: [
      { kind: "waste", quantity: "3", reason: "KURGUSAL E2E test tartımı" },
    ],
  });
}
export async function seedProduction(r: APIRequestContext) {
  const p = prefix(),
    supplier = await api<Party>(r, "/parties", {
      name: p + " Tedarikçi",
      roles: ["supplier"],
    }),
    producer = await api<Party>(r, "/parties", {
      name: p + " Üretici",
      roles: ["producer"],
    }),
    location = await api<Location>(r, "/locations", { name: p + " Depo" }),
    external = await api<Location>(r, "/locations", {
      name: p + " Üretici deposu",
      kind: "external_producer",
      party_id: producer.id,
    });
  const raw = [];
  for (const name of ["Et", "Baharat", "Kılıf"])
    raw.push(
      await api<Product>(r, "/products", {
        sku: p + "-" + raw.length,
        name: p + " " + name,
        type: "raw",
        base_unit: "kg",
      }),
    );
  const output = await api<Product>(r, "/products", {
    sku: p + "-SUC",
    name: p + " Sucuk",
    type: "finished",
    base_unit: "package",
    package_weight_kg: "1",
  });
  const quantities = ["100", "2", "5"];
  const receipt = await api<ReceiptDetail>(r, "/receipts", {
    supplier_id: supplier.id,
    location_id: location.id,
    lines: raw.map((product, i) => ({
      product_id: product.id,
      external_lot_code: p + "-RAW-" + i,
      quantity: quantities[i],
      total_cost: ["970.00", "48.00", "58.00"][i],
    })),
  });
  const op = await api<Operation>(r, "/operations", {
    code: p + "-URT",
    producer_id: producer.id,
  });
  return {
    p,
    location,
    external,
    output,
    quantities,
    lots: raw.map(
      (p) => receipt.lines.find((l) => l.product_id === p.id)!.lot_id,
    ),
    op,
  };
}
export async function closeProduction(
  r: APIRequestContext,
  s: Awaited<ReturnType<typeof seedProduction>>,
) {
  await api(r, "/operations/" + s.op.id + "/dispatch", {
    from_location_id: s.location.id,
    to_location_id: s.external.id,
    lines: s.lots.map((lot, i) => ({ lot_id: lot, quantity: s.quantities[i] })),
  });
  return api(r, "/operations/" + s.op.id + "/post", {
    consumed_inputs: s.lots.map((lot, i) => ({
      lot_id: lot,
      location_id: s.external.id,
      quantity: s.quantities[i],
    })),
    output_location_id: s.location.id,
    outputs: [
      { product_id: s.output.id, lot_code: s.p + "-SUC", quantity: "85" },
    ],
    service_costs: [{ amount: "467.50", invoice_reference: s.p + "-SERVICE" }],
    loss_quantity: "22",
    loss_reason: "KURGUSAL E2E üretim farkı",
  });
}
export async function stock(
  r: APIRequestContext,
  lot: string,
  location: string,
) {
  return (
    await api<{ items: Stock[] }>(
      r,
      `/stocks?lot_id=${lot}&location_id=${location}`,
    )
  ).items[0].quantity;
}

export async function apiAll<T>(r: APIRequestContext, path: string) {
  const out: T[] = [];
  let cursor: string | null = null;
  const seen = new Set<string>();
  do {
    const p: { items: T[]; next_cursor: string | null } = await api<{
      items: T[];
      next_cursor: string | null;
    }>(
      r,
      path +
        "?limit=100" +
        (cursor ? "&cursor=" + encodeURIComponent(cursor) : ""),
    );
    out.push(...p.items);
    cursor = p.next_cursor;
    if (cursor && seen.has(cursor)) throw new Error("Cyclic API cursor");
    if (cursor) seen.add(cursor);
  } while (cursor);
  return out;
}
