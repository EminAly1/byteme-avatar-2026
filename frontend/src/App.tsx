import { lazy, Suspense, useEffect, useRef, useState } from "react";
import {
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
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
  ShoppingBag,
  Truck,
  ArrowLeftRight,
  Network,
  ShieldAlert,
  Sparkles,
  Sprout,
  RefreshCw,
  Menu,
  ChevronRight,
  LockKeyhole,
  X,
  Search,
} from "lucide-react";
import { PageHeader } from "./components/presentation";
import { State } from "./components/ui";
const Products = lazy(() =>
  import("./pages/Catalog").then((m) => ({ default: m.Products })),
);
const Parties = lazy(() =>
  import("./pages/Catalog").then((m) => ({ default: m.Parties })),
);
const Locations = lazy(() =>
  import("./pages/Catalog").then((m) => ({ default: m.Locations })),
);
const Receipts = lazy(() =>
  import("./pages/Receipts").then((m) => ({ default: m.Receipts })),
);
const Stocks = lazy(() =>
  import("./pages/Stocks").then((m) => ({ default: m.Stocks })),
);
const Operations = lazy(() =>
  import("./pages/Operations").then((m) => ({ default: m.Operations })),
);
const OperationPage = lazy(() =>
  import("./pages/Operations").then((m) => ({ default: m.OperationPage })),
);
const Dashboard = lazy(() =>
  import("./pages/Dashboard").then((m) => ({ default: m.Dashboard })),
);
const Cuttings = lazy(() =>
  import("./pages/Cutting").then((m) => ({ default: m.Cuttings })),
);
const CuttingPage = lazy(() =>
  import("./pages/Cutting").then((m) => ({ default: m.CuttingPage })),
);
const Sales = lazy(() =>
  import("./pages/Sales").then((m) => ({ default: m.Sales })),
);
const SalePage = lazy(() =>
  import("./pages/Sales").then((m) => ({ default: m.SalePage })),
);
const Shipments = lazy(() =>
  import("./pages/Sales").then((m) => ({ default: m.Shipments })),
);
const Traceability = lazy(() =>
  import("./pages/Trace").then((m) => ({ default: m.Traceability })),
);
const Recalls = lazy(() =>
  import("./pages/Trace").then((m) => ({ default: m.Recalls })),
);
const RecallPage = lazy(() =>
  import("./pages/Trace").then((m) => ({ default: m.RecallPage })),
);
const Predictions = lazy(() =>
  import("./pages/Predictions").then((m) => ({ default: m.Predictions })),
);

const Movements = lazy(() =>
  import("./pages/Movements").then((m) => ({ default: m.Movements })),
);
const ReworkPage = lazy(() =>
  import("./pages/Reworks").then((m) => ({ default: m.ReworkPage })),
);
const Distributions = lazy(() =>
  import("./pages/Distributions").then((m) => ({ default: m.Distributions })),
);

const primary = [
  { path: "/", label: "Genel bakış", icon: LayoutDashboard },
  { path: "/uretim", label: "Dış üretim", icon: Factory },
  { path: "/parcalama", label: "Kuzu parçalama", icon: Scissors },
  { path: "/satislar", label: "Satışlar", icon: ShoppingBag },
  { path: "/sevkiyatlar", label: "Sevkiyatlar", icon: Truck },
  { path: "/dagitimlar", label: "İkinci kademe dağıtım", icon: Network },
  { path: "/hareketler", label: "Stok hareket merkezi", icon: ArrowLeftRight },
  { path: "/izlenebilirlik", label: "Lot izlenebilirliği", icon: Network },
  { path: "/geri-cagirma", label: "Geri çağırma", icon: ShieldAlert },
  { path: "/yapay-zeka", label: "Yapay zekâ tahminleri", icon: Sparkles },
];
const master = [
  { path: "/urunler", label: "Ürünler", icon: Boxes },
  { path: "/is-ortaklari", label: "İş ortakları", icon: Building2 },
  { path: "/depolar", label: "Depolar", icon: Warehouse },
  { path: "/alislar", label: "Alış ve lot girişi", icon: ClipboardList },
  { path: "/stoklar", label: "Stoklar", icon: Layers3 },
];
export function App() {
  const [menu, setMenu] = useState(false),
    location = useLocation(),
    client = useQueryClient(),
    fetching = useIsFetching(),
    sidebar = useRef<HTMLElement>(null),
    trigger = useRef<HTMLButtonElement>(null);
  const module = [...primary, ...master].find((x) =>
    x.path === "/"
      ? location.pathname === "/"
      : location.pathname.startsWith(x.path),
  );
  const title = module?.label || "Sayfa bulunamadı";
  const detail = location.pathname.split("/").filter(Boolean).length > 1;
  useEffect(() => {
    if (!menu) return;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const frame = requestAnimationFrame(() =>
      sidebar.current?.querySelector<HTMLButtonElement>(".nav-close")?.focus(),
    );
    return () => {
      cancelAnimationFrame(frame);
      document.body.style.overflow = overflow;
      trigger.current?.focus();
    };
  }, [menu]);
  useEffect(() => {
    const close = () => {
      if (innerWidth > 1100) setMenu(false);
    };
    window.addEventListener("resize", close);
    return () => window.removeEventListener("resize", close);
  }, []);
  function nav(items: typeof primary) {
    return items.map((x) => (
      <NavLink
        end={x.path === "/"}
        className={({ isActive }) => "nav-item " + (isActive ? "active" : "")}
        to={x.path}
        key={x.path}
        onClick={() => setMenu(false)}
      >
        <x.icon size={18} />
        <span>{x.label}</span>
        {location.pathname === x.path && <ChevronRight size={14} />}
      </NavLink>
    ));
  }
  return (
    <div className="app-layout">
      <a className="skip-link" href="#main-content">
        İçeriğe geç
      </a>
      <aside
        ref={sidebar}
        className={"sidebar " + (menu ? "open" : "")}
        aria-label="Yönetim menüsü"
        onKeyDown={(e) => {
          if (!menu) return;
          if (e.key === "Escape") setMenu(false);
          if (e.key === "Tab") {
            const nodes =
              sidebar.current?.querySelectorAll<HTMLElement>("a,button");
            if (!nodes?.length) return;
            const first = nodes[0],
              last = nodes[nodes.length - 1];
            if (e.shiftKey && document.activeElement === first) {
              e.preventDefault();
              last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
              e.preventDefault();
              first.focus();
            }
          }
        }}
      >
        <div className="brand-row">
          <NavLink to="/" className="brand" onClick={() => setMenu(false)}>
            <span className="brand-icon">
              <Sprout size={24} />
            </span>
            <div>
              ByteMe<small>ÜRETİM VE STOK YÖNETİMİ</small>
            </div>
          </NavLink>
          <button
            className="icon-button nav-close"
            aria-label="Menüyü kapat"
            onClick={() => setMenu(false)}
          >
            <X size={20} />
          </button>
        </div>
        <div className="workspace-label">
          <span className="workspace-dot" /> AVATAR 2026{" "}
          <span>Çalışma alanı</span>
        </div>
        <nav>
          <p className="nav-heading">OPERASYONLAR</p>
          {nav(primary)}
          <p className="nav-heading future-heading">KAYIT YÖNETİMİ</p>
          {nav(master)}
        </nav>
        <div className="sidebar-footer">
          <LockKeyhole size={17} />
          <div>
            Yerel çalışma alanı<small>ByteMe · AVATAR 2026</small>
          </div>
        </div>
      </aside>
      {menu && (
        <button
          className="sidebar-overlay"
          aria-label="Menü arka planını kapat"
          onClick={() => setMenu(false)}
          tabIndex={-1}
        />
      )}
      <div className="main-column" inert={menu}>
        <header className="topbar">
          <div className="breadcrumb">
            <button
              ref={trigger}
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
            <NavLink
              className="topbar-search"
              aria-label="Lot kaydı bul"
              to="/izlenebilirlik"
            >
              <Search size={16} />
              <span>Lot kaydı bul</span>
            </NavLink>
            <span className="connection">
              <i className={fetching ? "busy" : ""} />
              {fetching ? "Kayıtlar alınıyor" : "Yerel çalışma alanı"}
            </span>
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          <PageHeader
            title={
              detail
                ? ({ Satışlar: "Satış", "Dış üretim": "Üretim emri" }[title] ||
                    title) + " ayrıntısı"
                : title
            }
            description={
              location.pathname === "/"
                ? "Üretim, stok ve dağıtım kayıtlarını tek yerden yönetin."
                : undefined
            }
            action={
              <button
                className="button refresh"
                onClick={() => void client.invalidateQueries()}
                disabled={!!fetching}
              >
                <RefreshCw size={16} className={fetching ? "spin" : ""} />
                Yenile
              </button>
            }
          />
          <Suspense fallback={<State loading>{null}</State>}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/urunler" element={<Products />} />
              <Route path="/is-ortaklari" element={<Parties />} />
              <Route path="/depolar" element={<Locations />} />
              <Route path="/alislar" element={<Receipts />} />
              <Route path="/stoklar" element={<Stocks />} />
              <Route path="/uretim" element={<Operations />} />
              <Route path="/uretim/:id" element={<OperationPage />} />
              <Route path="/parcalama" element={<Cuttings />} />
              <Route path="/parcalama/:id" element={<CuttingPage />} />
              <Route path="/satislar" element={<Sales />} />
              <Route path="/satislar/:id" element={<SalePage />} />
              <Route path="/sevkiyatlar" element={<Shipments />} />
              <Route path="/dagitimlar" element={<Distributions />} />
              <Route path="/dagitimlar/:id" element={<Distributions />} />
              <Route path="/hareketler" element={<Movements />} />
              <Route path="/hareketler/rework/:id" element={<ReworkPage />} />
              <Route path="/izlenebilirlik" element={<Traceability />} />
              <Route path="/geri-cagirma" element={<Recalls />} />
              <Route path="/geri-cagirma/:id" element={<RecallPage />} />
              <Route path="/yapay-zeka" element={<Predictions />} />
              {Object.entries({
                parcalama: "parcalama",
                satis: "satislar",
                izleme: "izlenebilirlik",
                recall: "geri-cagirma",
                ai: "yapay-zeka",
              }).map(([from, to]) => (
                <Route
                  key={from}
                  path={"/plan/" + from}
                  element={<Navigate replace to={"/" + to} />}
                />
              ))}
              <Route
                path="*"
                element={
                  <section className="panel planned">
                    <h2>Sayfa bulunamadı</h2>
                    <NavLink className="button" to="/">
                      Genel bakışa dön
                    </NavLink>
                  </section>
                }
              />
            </Routes>
          </Suspense>
          <footer className="page-footer">
            <span>ByteMe · AVATAR 2026</span>
            <span>Kayıtlı lotlar. Gerçek maliyetler.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
