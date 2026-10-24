import { useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { useIsFetching, useQueryClient } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Boxes,
  Building2,
  Warehouse,
  ClipboardList,
  Layers3,
  Factory,
  Scissors,
  ChartNoAxesCombined,
  Network,
  ShieldAlert,
  Sparkles,
  Sprout,
  RefreshCw,
  Menu,
  ChevronRight,
  ArrowUpRight,
  LockKeyhole,
} from "lucide-react";
import { Products, Parties, Locations } from "./pages/Catalog";
import { Receipts } from "./pages/Receipts";
import { Stocks } from "./pages/Stocks";
import { Operations, OperationPage } from "./pages/Operations";
import { Dashboard } from "./pages/Dashboard";

const primary = [
  { path: "/", label: "Genel bakış", icon: LayoutDashboard },
  { path: "/urunler", label: "Ürünler", icon: Boxes },
  { path: "/is-ortaklari", label: "İş ortakları", icon: Building2 },
  { path: "/depolar", label: "Depolar", icon: Warehouse },
  { path: "/alislar", label: "Alış ve lot girişi", icon: ClipboardList },
  { path: "/stoklar", label: "Stoklar", icon: Layers3 },
  { path: "/uretim", label: "Dış üretim", icon: Factory },
];
const future = [
  { path: "/plan/parcalama", label: "Kuzu parçalama", icon: Scissors },
  { path: "/plan/satis", label: "Satış raporları", icon: ChartNoAxesCombined },
  { path: "/plan/izleme", label: "Lot izlenebilirliği", icon: Network },
  { path: "/plan/recall", label: "Geri çağırma", icon: ShieldAlert },
  { path: "/plan/ai", label: "Yapay zekâ tahminleri", icon: Sparkles },
];
function Planned({ title }: { title: string }) {
  return (
    <section className="planned panel">
      <div className="planned-icon">
        <Layers3 size={32} />
      </div>
      <span className="eyebrow">YOL HARİTASI</span>
      <h2>{title}</h2>
      <span className="badge amber">Geliştirme aşamasında</span>
      <p>
        Bu modülün backend işlemleri henüz uygulanmadı. Buradan gerçek bir işlem
        başlatılamaz.
      </p>
      <NavLink to="/" className="button">
        Genel bakışa dön <ArrowUpRight size={16} />
      </NavLink>
    </section>
  );
}
export function App() {
  const [menu, setMenu] = useState(false),
    location = useLocation(),
    client = useQueryClient(),
    fetching = useIsFetching();
  const title =
    [...primary, ...future].find((x) =>
      x.path === "/"
        ? location.pathname === "/"
        : location.pathname.startsWith(x.path),
    )?.label || "Sayfa bulunamadı";
  return (
    <div className="app-layout">
      <a href="#main-content" className="skip-link">
        İçeriğe geç
      </a>
      <aside
        className={"sidebar " + (menu ? "open" : "")}
        aria-label="Yönetim menüsü"
      >
        <NavLink to="/" className="brand" onClick={() => setMenu(false)}>
          <span className="brand-icon">
            <Sprout size={25} />
          </span>
          <div>
            ByteMe<small>AVATAR 2026</small>
          </div>
        </NavLink>
        <div className="workspace-label">GIDA ÜRETİM YÖNETİMİ</div>
        <nav>
          <p className="nav-heading">ÇALIŞMA ALANI</p>
          {primary.map((x) => (
            <NavLink
              end={x.path === "/"}
              className={({ isActive }) =>
                "nav-item " + (isActive ? "active" : "")
              }
              to={x.path}
              key={x.path}
              onClick={() => setMenu(false)}
            >
              <x.icon size={19} />
              <span>{x.label}</span>
              {location.pathname === x.path && <ChevronRight size={15} />}
            </NavLink>
          ))}
          <p className="nav-heading future-heading">SONRAKİ AŞAMA</p>
          {future.map((x) => (
            <NavLink
              className={({ isActive }) =>
                "nav-item future " + (isActive ? "active" : "")
              }
              to={x.path}
              key={x.path}
              onClick={() => setMenu(false)}
            >
              <x.icon size={18} />
              <span>{x.label}</span>
              <span className="nav-dot" />
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <LockKeyhole size={17} />
          <div>
            Yerel geliştirme<small>Yalnızca bu bilgisayarda</small>
          </div>
        </div>
      </aside>
      {menu && (
        <button
          className="sidebar-overlay"
          aria-label="Menüyü kapat"
          onClick={() => setMenu(false)}
        />
      )}
      <div className="main-column">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button menu-button"
              aria-label="Menüyü aç"
              aria-expanded={menu}
              onClick={() => setMenu(!menu)}
            >
              <Menu size={21} />
            </button>
            <span>Çalışma alanı</span>
            <ChevronRight size={15} />
            <strong>{title}</strong>
          </div>
          <div className="topbar-right">
            <span className="connection">
              <i className={fetching ? "busy" : ""} />
              {fetching ? "Kayıtlar alınıyor" : "Yerel demo"}
            </span>
            <span className="avatar" aria-hidden="true">
              B
            </span>
          </div>
        </header>
        <main id="main-content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">BYTEME / OPERASYONLAR</p>
              <h1>
                {location.pathname.startsWith("/uretim/")
                  ? "Üretim emri ayrıntısı"
                  : title}
              </h1>
            </div>
            <button
              className="button refresh"
              onClick={() => void client.invalidateQueries()}
              disabled={!!fetching}
            >
              <RefreshCw size={16} className={fetching ? "spin" : ""} />
              Yenile
            </button>
          </div>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/urunler" element={<Products />} />
            <Route path="/is-ortaklari" element={<Parties />} />
            <Route path="/depolar" element={<Locations />} />
            <Route path="/alislar" element={<Receipts />} />
            <Route path="/stoklar" element={<Stocks />} />
            <Route path="/uretim" element={<Operations />} />
            <Route path="/uretim/:id" element={<OperationPage />} />
            {future.map((x) => (
              <Route
                key={x.path}
                path={x.path}
                element={<Planned title={x.label} />}
              />
            ))}
            <Route
              path="*"
              element={
                <div className="panel planned">
                  <h2>Sayfa bulunamadı</h2>
                  <NavLink className="button" to="/">
                    Genel bakışa dön
                  </NavLink>
                </div>
              }
            />
          </Routes>
          <footer className="page-footer">
            <span>ByteMe · AVATAR 2026</span>
            <span>Kayıtlı lotlar. Gerçek maliyetler.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
