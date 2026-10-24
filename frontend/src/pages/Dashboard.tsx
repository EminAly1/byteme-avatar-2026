import { Link } from "react-router-dom";
import {
  Boxes,
  ClipboardList,
  Factory,
  PackageCheck,
  ArrowUpRight,
  ShieldAlert,
} from "lucide-react";
import { useCatalog, useRecords } from "../lib/data";
import { Badge, Section, State, Table } from "../components/ui";
import { amount, eur, positive, units } from "../lib/format";
import type { Operation, Receipt, Stock } from "../lib/types";

export function Dashboard() {
  const data = useCatalog(),
    stocks = useRecords<Stock>("/stocks"),
    receipts = useRecords<Receipt>("/receipts"),
    operations = useRecords<Operation>("/operations");
  const current = stocks.data?.filter((x) => positive(x.quantity)) || [];
  const unavailable = current.filter(
    (x) => !positive(x.available_quantity),
  ).length;
  const stats = [
    {
      label: "Ürün kartı",
      value: data.products.length,
      icon: Boxes,
      note: "Tüm ürün türleri",
    },
    {
      label: "Stoklu lot / konum",
      value: current.length,
      icon: PackageCheck,
      note: "Pozitif bakiye kayıtları",
    },
    {
      label: "Alış kaydı",
      value: receipts.data?.length || 0,
      icon: ClipboardList,
      note: "Kaydedilmiş alışlar",
    },
    {
      label: "Açık üretim emri",
      value: operations.data?.filter((x) => x.status === "draft").length || 0,
      icon: Factory,
      note: "Kapanış bekleyen emirler",
    },
  ];
  return (
    <State
      loading={
        data.loading ||
        stocks.isPending ||
        receipts.isPending ||
        operations.isPending
      }
      error={data.error || stocks.error || receipts.error || operations.error}
    >
      <div className="stack">
        <div className="welcome">
          <div>
            <Badge tone="green">OPERASYON MERKEZİ</Badge>
            <h2>
              Üretimin her adımı,
              <br />
              aynı kayıt zincirinde.
            </h2>
            <p>
              Alıştan mamul kabulüne kadar lotları, stokları ve gerçek
              maliyetleri yönetin.
            </p>
            <Link className="button primary" to="/alislar">
              Yeni alış kaydı <ArrowUpRight size={17} />
            </Link>
          </div>
          <div className="welcome-mark" aria-hidden="true">
            <div className="mark-ring">
              <Boxes size={64} />
            </div>
            <span>
              HAMMADDE <span>→</span> ÜRETİM <span>→</span> MAMUL
            </span>
          </div>
        </div>
        <div className="stat-grid">
          {stats.map((x) => (
            <div className="stat" key={x.label}>
              <div className="stat-top">
                <span>{x.label}</span>
                <x.icon size={19} />
              </div>
              <strong>{x.value}</strong>
              <small>{x.note}</small>
            </div>
          ))}
        </div>
        <p className="caption">
          Özet, tamamı yüklenen API kayıtlarına dayanır. Stok miktarları farklı
          birimlerle toplanmaz; satış ve kâr metrikleri henüz sunulmaz.
        </p>
        {unavailable > 0 && (
          <div className="notice warning">
            <ShieldAlert size={20} />
            {unavailable} stoklu lot/konum kaydının kullanılabilir miktarı
            sıfır. Stok ekranından blok, tarih ve karantina durumunu inceleyin.
          </div>
        )}
        <div className="dashboard-grid">
          <Section
            title="Son üretim emirleri"
            subtitle="Kaydedilen en yeni emirler"
            action={
              <Link className="text-button" to="/uretim">
                Tümünü gör <ArrowUpRight size={15} />
              </Link>
            }
          >
            <Table
              headers={["Emir", "Durum", "Gerçek maliyet"]}
              empty={!operations.data?.length}
            >
              {[...(operations.data || [])]
                .sort((a, b) => b.created_at.localeCompare(a.created_at))
                .slice(0, 5)
                .map((x) => (
                  <tr key={x.id}>
                    <td>
                      <Link className="text-button code" to={"/uretim/" + x.id}>
                        {x.code}
                      </Link>
                    </td>
                    <td>
                      <Badge tone={x.status === "posted" ? "green" : "amber"}>
                        {x.status === "posted" ? "Kapandı" : "Açık"}
                      </Badge>
                    </td>
                    <td>{x.status === "posted" ? eur(x.total_cost) : "—"}</td>
                  </tr>
                ))}
            </Table>
          </Section>
          <Section
            title="Depodaki lotlar"
            subtitle="İlk beş pozitif bakiye kaydı"
            action={
              <Link className="text-button" to="/stoklar">
                Stokları aç <ArrowUpRight size={15} />
              </Link>
            }
          >
            <Table headers={["Lot / Ürün", "Miktar"]} empty={!current.length}>
              {current.slice(0, 5).map((x) => {
                const p = data.products.find((p) => p.id === x.product_id);
                return (
                  <tr key={x.lot_id + x.location_id}>
                    <td>
                      <strong className="code">
                        {
                          data.lots.find((l) => l.id === x.lot_id)
                            ?.external_code
                        }
                      </strong>
                      <small>
                        {p?.name} ·{" "}
                        {
                          data.locations.find((l) => l.id === x.location_id)
                            ?.name
                        }
                      </small>
                    </td>
                    <td>
                      {amount(x.quantity)} {p && units[p.base_unit]}
                    </td>
                  </tr>
                );
              })}
            </Table>
          </Section>
        </div>
      </div>
    </State>
  );
}
