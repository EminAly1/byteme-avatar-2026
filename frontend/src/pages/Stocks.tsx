import { useSearchParams } from "react-router-dom";
import { useState } from "react";
import { useCatalog, useRecords } from "../lib/data";
import { Section, State, Table, Badge } from "../components/ui";
import {
  amount,
  dateTime,
  locationKinds,
  movementTypes,
  positive,
  short,
  units,
} from "../lib/format";
import type { Movement, Stock } from "../lib/types";

export function Stocks() {
  const [search] = useSearchParams();
  const data = useCatalog(),
    [product, setProduct] = useState(search.get("product") || ""),
    [lot, setLot] = useState(search.get("lot") || ""),
    [location, setLocation] = useState(search.get("location") || ""),
    [tab, setTab] = useState("stocks");
  const stock = useRecords<Stock>("/stocks"),
    movements = useRecords<Movement>("/stock-movements");
  const filtered =
    stock.data?.filter(
      (x) =>
        (!product || x.product_id === product) &&
        (!lot || x.lot_id === lot) &&
        (!location || x.location_id === location),
    ) || [];
  const history =
    movements.data?.filter(
      (x) =>
        (!product ||
          data.lots.find((l) => l.id === x.lot_id)?.product_id === product) &&
        (!lot || x.lot_id === lot) &&
        (!location || x.location_id === location),
    ) || [];
  return (
    <State
      loading={data.loading || stock.isPending || movements.isPending}
      error={data.error || stock.error || movements.error}
    >
      <Section
        title="Stok görünümü"
        subtitle="Ürün, lot ve konuma göre gerçek bakiyeler. Farklı ölçü birimleri toplanmaz."
      >
        <div className="filters">
          <label>
            Ürün
            <select
              aria-label="Ürün"
              value={product}
              onChange={(e) => {
                setProduct(e.target.value);
                setLot("");
              }}
            >
              <option value="">Tüm ürünler</option>
              {data.products.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Lot
            <select
              aria-label="Lot"
              value={lot}
              onChange={(e) => setLot(e.target.value)}
            >
              <option value="">Tüm lotlar</option>
              {data.lots
                .filter((x) => !product || x.product_id === product)
                .map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.external_code} · {short(x.id)}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Depo / konum
            <select
              aria-label="Depo / konum"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            >
              <option value="">Tüm konumlar</option>
              {data.locations.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="tabs" role="group" aria-label="Stok görünümü">
          <button
            className={tab === "stocks" ? "active" : ""}
            onClick={() => setTab("stocks")}
          >
            Lot bakiyeleri
          </button>
          <button
            className={tab === "history" ? "active" : ""}
            onClick={() => setTab("history")}
          >
            Hareket geçmişi
          </button>
        </div>
        {tab === "stocks" ? (
          <Table
            headers={["Ürün / Lot", "Konum", "Stok", "Kullanılabilir", "Durum"]}
            empty={!filtered.length}
          >
            {filtered.map((x) => {
              const p = data.products.find((p) => p.id === x.product_id),
                l = data.locations.find((l) => l.id === x.location_id);
              return (
                <tr key={x.lot_id + x.location_id}>
                  <td>
                    <strong>{p?.name}</strong>
                    <small className="sub-code">
                      {data.lots.find((l) => l.id === x.lot_id)?.external_code}{" "}
                      · {short(x.lot_id)}
                    </small>
                  </td>
                  <td>
                    {l?.name}
                    <small>{l && locationKinds[l.kind]}</small>
                  </td>
                  <td>
                    {amount(x.quantity)} {p && units[p.base_unit]}
                  </td>
                  <td>
                    {amount(x.available_quantity)} {p && units[p.base_unit]}
                  </td>
                  <td>
                    <Badge
                      tone={
                        x.blocked
                          ? "red"
                          : positive(x.quantity) &&
                              !positive(x.available_quantity)
                            ? "amber"
                            : positive(x.quantity)
                              ? "green"
                              : ""
                      }
                    >
                      {x.blocked
                        ? "Bloke"
                        : positive(x.quantity) &&
                            !positive(x.available_quantity)
                          ? "Kullanılamaz"
                          : positive(x.quantity)
                            ? "Kullanılabilir"
                            : "Bakiye yok"}
                    </Badge>
                  </td>
                </tr>
              );
            })}
          </Table>
        ) : (
          <Table
            headers={["Tarih", "Hareket", "Lot", "Konum", "Miktar"]}
            empty={!history.length}
          >
            {[...history]
              .sort((a, b) => b.created_at.localeCompare(a.created_at))
              .map((x) => {
                const p = data.products.find(
                  (p) =>
                    p.id ===
                    data.lots.find((l) => l.id === x.lot_id)?.product_id,
                );
                return (
                  <tr key={x.id}>
                    <td>{dateTime(x.created_at)}</td>
                    <td>{movementTypes[x.type] || "Stok hareketi"}</td>
                    <td className="code">
                      {data.lots.find((l) => l.id === x.lot_id)
                        ?.external_code || short(x.lot_id)}
                    </td>
                    <td>
                      {data.locations.find((l) => l.id === x.location_id)?.name}
                    </td>
                    <td
                      className={
                        x.quantity.startsWith("-") ? "negative" : "positive"
                      }
                    >
                      {amount(x.quantity)} {p && units[p.base_unit]}
                    </td>
                  </tr>
                );
              })}
          </Table>
        )}
        <p className="table-foot">
          {tab === "stocks" ? filtered.length : history.length} kayıt • Tüm API
          sayfaları yüklendi. Durumlar backend kullanılabilir miktarına dayanır.
        </p>
      </Section>
    </State>
  );
}
