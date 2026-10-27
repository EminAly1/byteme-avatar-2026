import { DashboardAlerts } from "../components/Alerts";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { Link } from "react-router-dom";
import {
  Boxes,
  ClipboardList,
  Factory,
  PackageCheck,
  ArrowUpRight,
  ShieldAlert,
  Scissors,
  ShoppingBag,
  Truck,
  Network,
  Sparkles,
} from "lucide-react";
import { useCatalog, useRecords } from "../lib/data";
import { Badge, Section, State, Table } from "../components/ui";
import { StatCard } from "../components/presentation";
import { amount, dateTime, eur, positive, units, short } from "../lib/format";
import type { Sale, Shipment } from "../lib/modules";
import type { Operation, Receipt, Stock } from "../lib/types";
export function Dashboard() {
  const mobile = useMediaQuery("(max-width: 600px)"),
    limit = mobile ? 2 : 4;
  const data = useCatalog(),
    stocks = useRecords<Stock>("/stocks"),
    receipts = useRecords<Receipt>("/receipts"),
    operations = useRecords<Operation>("/operations"),
    sales = useRecords<Sale>("/sales"),
    shipments = useRecords<Shipment>("/shipments");
  const current = stocks.data?.filter((x) => positive(x.quantity)) || [],
    unavailable = current.filter((x) => !positive(x.available_quantity)).length;
  const stats = [
    {
      label: "Açık üretim emri",
      value:
        operations.data?.filter(
          (x) => x.status === "draft" && x.kind === "external_production",
        ).length || 0,
      icon: Factory,
      note: "Kapanış bekleyen",
    },
    {
      label: "Stoklu lot / konum",
      value: current.length,
      icon: PackageCheck,
      note: "Pozitif bakiye",
    },
    {
      label: "Kesin satış",
      value: sales.data?.length || 0,
      icon: ShoppingBag,
      note: "Onaylanmış kayıt",
    },
    {
      label: "Sevkiyat",
      value: shipments.data?.length || 0,
      icon: Truck,
      note: "Teslim belgesi",
    },
    {
      label: "Alış kaydı",
      value: receipts.data?.length || 0,
      icon: ClipboardList,
      note: "Kaydedilmiş alış",
    },
    {
      label: "Ürün kartı",
      value: data.products.length,
      icon: Boxes,
      note: "Tüm ürün türleri",
    },
  ];
  const latest = <T extends { created_at: string }>(v: T[] | undefined) =>
    [...(v || [])]
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .slice(0, limit);
  return (
    <State
      loading={
        data.loading ||
        [stocks, receipts, operations, sales, shipments].some(
          (q) => q.isPending,
        )
      }
      error={
        data.error ||
        [stocks, receipts, operations, sales, shipments].find((q) => q.error)
          ?.error
      }
    >
      <div className="stack dashboard">
        <div className="overview-heading">
          <h2>Operasyon özeti</h2>
          <span>Kayıtlı işlemler · Farklı stok birimleri ayrı gösterilir</span>
        </div>
        <div className="stat-grid dashboard-stats">
          {stats.map((s) => (
            <StatCard
              key={s.label}
              label={s.label}
              value={s.value}
              note={s.note}
              icon={<s.icon size={18} />}
            />
          ))}
        </div>
        <DashboardAlerts />
        {unavailable > 0 && (
          <div className="notice warning">
            <ShieldAlert size={20} />
            <div>
              <strong>{unavailable} stok kaydı kullanılamıyor</strong>
              <p>
                Bloke, tarih veya karantina durumlarını stok ekranından
                inceleyin.
              </p>
            </div>
            <Link className="text-button" to="/stoklar">
              Stokları incele <ArrowUpRight size={15} />
            </Link>
          </div>
        )}
        <section className="quick-section" aria-label="Hızlı işlemler">
          <div className="section-title">
            <h2>Nasıl ilerlemek istersiniz?</h2>
            <span>Yeni işlem başlatın</span>
          </div>
          <div className="quick-actions">
            {[
              {
                to: "/parcalama",
                icon: Scissors,
                label: "Kesim başlat",
                note: "Reçete ve fiilî tartım",
              },
              {
                to: "/satislar",
                icon: ShoppingBag,
                label: "Lotlu satış",
                note: "Müşteri ve uygun lot",
              },
              {
                to: "/izlenebilirlik",
                icon: Network,
                label: "Lotu izle",
                note: "Kaynak ve bilinen alıcılar",
              },
              {
                to: "/yapay-zeka",
                icon: Sparkles,
                label: "Tahmin oluştur",
                note: "Üretim ve parçalama",
              },
            ].map((x) => (
              <Link key={x.to} to={x.to} className="quick-link">
                <span className="quick-icon">
                  <x.icon size={20} />
                </span>
                <span>
                  <strong>{x.label}</strong>
                  <small>{x.note}</small>
                </span>
                <ArrowUpRight size={16} />
              </Link>
            ))}
          </div>
        </section>
        <div className="dashboard-grid">
          <Section
            title="Son üretim ve kesimler"
            subtitle={mobile ? "En yeni iki kayıt" : "En yeni dört kayıt"}
            action={
              <Link className="text-button" to="/uretim">
                Tüm üretimler <ArrowUpRight size={15} />
              </Link>
            }
          >
            <Table
              headers={["İşlem", "Durum", "Gerçek maliyet"]}
              empty={!operations.data?.length}
            >
              {latest(operations.data).map((o) => (
                <tr key={o.id}>
                  <td>
                    <Link
                      className="text-button"
                      to={
                        (o.kind === "cutting"
                          ? "/parcalama/"
                          : o.kind === "rework"
                            ? "/hareketler/rework/"
                            : "/uretim/") + o.id
                      }
                    >
                      {o.code}
                    </Link>
                    <small>
                      {o.kind === "cutting"
                        ? "Kuzu parçalama"
                        : o.kind === "rework"
                          ? "Yeniden işleme"
                          : "Dış üretim"}
                    </small>
                  </td>
                  <td>
                    <Badge tone={o.status === "posted" ? "green" : "amber"}>
                      {o.status === "posted" ? "Kapandı" : "Açık"}
                    </Badge>
                  </td>
                  <td>
                    {o.status === "posted"
                      ? eur(o.total_cost)
                      : "Kapanış bekleniyor"}
                  </td>
                </tr>
              ))}
            </Table>
          </Section>
          <Section
            title="Son satışlar"
            subtitle="Onaylanmış satış kayıtları"
            action={
              <Link className="text-button" to="/satislar">
                Tüm satışlar <ArrowUpRight size={15} />
              </Link>
            }
          >
            <Table
              headers={["Müşteri / tarih", "Satış tutarı", "Ayrıntı"]}
              empty={!sales.data?.length}
            >
              {latest(sales.data).map((s) => (
                <tr key={s.id}>
                  <td>
                    <strong>
                      {data.parties.find((p) => p.id === s.customer_id)?.name}
                    </strong>
                    <small>{dateTime(s.sold_at)}</small>
                  </td>
                  <td>{eur(s.total_amount)}</td>
                  <td>
                    <Link className="text-button" to={"/satislar/" + s.id}>
                      Satışı aç
                    </Link>
                  </td>
                </tr>
              ))}
            </Table>
          </Section>
          <Section
            title="Son sevkiyatlar"
            subtitle="Kayıtlı teslim belgeleri"
            action={
              <Link className="text-button" to="/sevkiyatlar">
                Tüm sevkiyatlar <ArrowUpRight size={15} />
              </Link>
            }
          >
            <Table
              headers={["Alıcı", "Teslim zamanı", "Ayrıntı"]}
              empty={!shipments.data?.length}
            >
              {latest(shipments.data).map((s) => (
                <tr key={s.id}>
                  <td>
                    <strong>{s.recipient_name}</strong>
                    <small>
                      {s.sale_id
                        ? "Satışa bağlı sevkiyat"
                        : "Bağımsız sevkiyat"}
                    </small>
                  </td>
                  <td>{dateTime(s.shipped_at)}</td>
                  <td>
                    <Link
                      className="text-button"
                      to={"/sevkiyatlar?shipment=" + s.id}
                    >
                      Belgeyi aç
                    </Link>
                  </td>
                </tr>
              ))}
            </Table>
          </Section>
          <Section
            title="Depodaki lotlar"
            subtitle={
              mobile
                ? "Pozitif bakiyeden ilk iki konum"
                : "Pozitif bakiyeden ilk dört konum"
            }
            action={
              <Link className="text-button" to="/stoklar">
                Tüm stoklar <ArrowUpRight size={15} />
              </Link>
            }
          >
            <Table
              headers={["Ürün / lot", "Konum", "Miktar"]}
              empty={!current.length}
            >
              {current.slice(0, limit).map((s) => {
                const p = data.products.find((p) => p.id === s.product_id),
                  l = data.lots.find((l) => l.id === s.lot_id);
                return (
                  <tr key={s.lot_id + s.location_id}>
                    <td>
                      <strong>{p?.name}</strong>
                      <Link
                        className="text-button code"
                        to={"/izlenebilirlik?lot=" + s.lot_id}
                      >
                        {l?.external_code || short(s.lot_id)}
                      </Link>
                    </td>
                    <td>
                      {data.locations.find((x) => x.id === s.location_id)?.name}
                    </td>
                    <td>
                      {amount(s.quantity)} {p && units[p.base_unit]}
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
