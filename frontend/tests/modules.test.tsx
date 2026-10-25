import { fireEvent, render, screen } from "@testing-library/react";
import { it, expect, vi } from "vitest";
import { PredictionResult } from "../src/pages/Predictions";
import type { Prediction } from "../src/lib/modules";
import { request, ApiError } from "../src/lib/api";
const prediction: Prediction = {
  id: "00000000-0000-4000-8000-000000000001",
  kind: "production",
  operation_id: null,
  predicted_at: "2026-10-25T08:00:00Z",
  features: { meat_kg: "100" },
  context: {},
  model_version: "production-ridge-v1-test",
  data_origin: "SYNTHETIC",
  prediction_limitations: ["Gerçek işletme doğruluğu yok."],
  predicted_finished_quantity: "86.3",
  predicted_yield_ratio: "0.807",
  predicted_total_cost_eur: "1517.6",
  predicted_ekp_eur_per_unit: "17.57",
  comparison: {
    predicted_finished_quantity: {
      predicted: "86.3",
      actual: null,
      absolute_deviation: null,
      percentage_deviation: null,
    },
  },
};
it("tahmin ayrı etiketlenir; gerçekleşme null ise sayı uydurulmaz", () => {
  render(<PredictionResult prediction={prediction} />);
  expect(screen.getByText("Henüz gerçekleşmedi")).toBeVisible();
  expect(screen.getByText("SYNTHETIC")).toBeVisible();
  expect(
    screen.getByText(/Gerçek işletme verileriyle doğruluğu henüz/),
  ).toBeVisible();
  expect(screen.getByText(prediction.id)).not.toBeVisible();
  fireEvent.click(screen.getByText('Model bilgisi, teknik referans ve tam hassasiyet'));
  fireEvent.click(screen.getByText('Tahmin kaydı', {exact:false, selector:'summary'}));
  expect(screen.getByText(prediction.id)).toBeVisible();
  expect(screen.getByText(/production-ridge-v1-test/)).toBeVisible();
});
it("backend gerçekleşmesi ve mutlak/yüzdesel sapma ayrı sütunlarda gösterilir", () => {
  render(
    <PredictionResult
      prediction={{
        ...prediction,
        comparison: {
          predicted_finished_quantity: {
            predicted: "86.3",
            actual: "85",
            absolute_deviation: "1.3",
            percentage_deviation: "1.529412",
          },
        },
      }}
    />,
  );
  expect(screen.getByRole("cell", { name: "85 paket" })).toBeVisible();
  expect(screen.getByRole("cell", { name: "1,3 paket" })).toBeVisible();
  expect(screen.getByRole("cell", { name: "1,53%" })).toBeVisible();
  fireEvent.click(screen.getByText('Model bilgisi, teknik referans ve tam hassasiyet'));
  expect(screen.getByText(/"percentage_deviation": "1.529412"/)).toBeVisible();
});
it("MODEL_UNAVAILABLE 503 sahte tahmin yerine anlaşılır hata üretir", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        Response.json(
          { error: { code: "MODEL_UNAVAILABLE", message: "Model yok" } },
          { status: 503 },
        ),
      ),
  );
  try {
    await expect(request("/predictions/models")).rejects.toMatchObject({
      status: 503,
      code: "MODEL_UNAVAILABLE",
      message: expect.stringContaining("Tahmin üretilmedi"),
    });
  } finally {
    vi.unstubAllGlobals();
  }
});
it("LOT_BLOCKED 409 için aksiyon öneren Türkçe mesaj gösterilir", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockImplementation(async () =>
        Response.json({ error: { code: "LOT_BLOCKED" } }, { status: 409 }),
      ),
  );
  try {
    await expect(request("/sales")).rejects.toBeInstanceOf(ApiError);
    await expect(request("/sales")).rejects.toMatchObject({
      message: expect.stringContaining("geri çağırma kapsamında bloke"),
    });
  } finally {
    vi.unstubAllGlobals();
  }
});
