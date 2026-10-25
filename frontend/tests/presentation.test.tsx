import { render, screen, fireEvent, act } from "@testing-library/react";
import { it, expect, vi } from "vitest";
import {
  displayDecimal,
  displayEuro,
  displayYield,
} from "../src/lib/presentation";
import { RecordId, ProcessSteps } from "../src/components/presentation";
import { Table } from "../src/components/ui";
it("gösterim yuvarlaması büyük ondalıkları, işareti ve eldeyi kesin korur", () => {
  expect(displayDecimal("999999999999.99995", 3)).toBe("1.000.000.000.000");
  expect(displayDecimal("-0.0004", 3)).toBe("0");
  expect(displayDecimal("-12.3456", 3)).toBe("-12,346");
  expect(displayEuro("18.155")).toBe("18,16 €");
  expect(displayEuro("0")).toBe("0,00 €");
  expect(displayDecimal(null)).toBe("—");
});
it("verim yalnız gösterimde yüzdeye dönüşür; ham metin değişmez", () => {
  const source = "0.823456789";
  expect(displayYield(source)).toBe("82,35%");
  expect(source).toBe("0.823456789");
  expect(displayYield("1")).toBe("100%");
  expect(displayYield(null)).toBe("—");
});
it("teknik referans isteğe bağlı açılır ve aynı tam kimlik kopyalanır", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  vi.stubGlobal("navigator", { clipboard: { writeText } });
  try {
    render(<RecordId id="real-reference-123" label="Lot UUID" />);
    expect(screen.getByText("real-reference-123")).not.toBeVisible();
    fireEvent.click(screen.getByText(/Lot kaydı/));
    expect(screen.getByText("real-reference-123")).toBeVisible();
    await act(async () =>
      fireEvent.click(
        screen.getByRole("button", { name: /kimliğini kopyala/ }),
      ),
    );
    expect(writeText).toHaveBeenCalledWith("real-reference-123");
    expect(screen.getByRole("status")).toHaveTextContent("Kopyalandı");
  } finally {
    vi.unstubAllGlobals();
  }
});
it("adımlarda tamamlanan ile mevcut adım ayrı ve erişilebilirdir", () => {
  render(<ProcessSteps steps={["Reçete", "Tartım", "Sonuç"]} current={1} />);
  const steps = screen.getAllByRole("listitem");
  expect(steps[0]).toHaveClass("complete");
  expect(steps[1]).toHaveAttribute("aria-current", "step");
  expect(steps[2]).not.toHaveClass("complete");
});
it("mobil kart aynı satırın ürününü, miktarını ve gerçek maliyetini saklamaz", () => {
  vi.stubGlobal("matchMedia", () => ({
    matches: true,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
  try {
    render(
      <Table headers={["Ürün / lot", "Miktar", "Maliyet"]}>
        <tr>
          <td>But · LOT-1</td>
          <td>5 kg</td>
          <td>72,00 €</td>
        </tr>
      </Table>,
    );
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("article")).toHaveTextContent(
      "But · LOT-1Miktar5 kgMaliyet72,00 €",
    );
  } finally {
    vi.unstubAllGlobals();
  }
});
