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
  RefreshCw,
  Menu,
  ChevronRight,
  LockKeyhole,
  X,
  Search,
  Smartphone,
} from "lucide-react";
import { navigation, matchesEntry } from "./lib/navigation";
import { useMediaQuery } from "./hooks/useMediaQuery";
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

const Alerts = lazy(() =>
  import("./pages/Alerts").then((m) => ({ default: m.Alerts })),
);
const Documents = lazy(() =>
  import("./pages/Documents").then((m) => ({ default: m.Documents })),
);
const SaleDocument = lazy(() =>
  import("./pages/Documents").then((m) => ({ default: m.SaleDocument })),
);

const ApkDownloadDialog = lazy(() => import("./features/apk-download/ApkDownloadDialog"));

export function App() {
  const [apkOpen, setApkOpen] = useState(false);
  const [menu, setMenu] = useState(false),
    location = useLocation(),
    client = useQueryClient(),
    fetching = useIsFetching(),
    sidebar = useRef<HTMLElement>(null),
    trigger = useRef<HTMLButtonElement>(null);
  const compact = useMediaQuery("(max-width: 1100px)");
  const module = navigation
    .flatMap((g) => g.items)
    .find((x) => matchesEntry(x.path, location.pathname, location.search));
  const activeGroup = navigation.find((g) =>
    g.items.some((x) => x === module),
  )?.label;
  const [openGroups, setOpenGroups] = useState<string[]>(
    activeGroup ? [activeGroup] : [],
  );
  useEffect(() => {
    if (activeGroup)
      setOpenGroups((groups) =>
        groups.includes(activeGroup) ? groups : [...groups, activeGroup],
      );
  }, [activeGroup]);
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
  return (
    <div className="app-layout">
      <a className="skip-link" href="#main-content">
        İçeriğe geç
      </a>
      <aside
        ref={sidebar}
        inert={compact && !menu}
        aria-hidden={compact && !menu}
        className={"sidebar " + (menu ? "open" : "")}
        aria-label="Yönetim menüsü"
        onKeyDown={(e) => {
          if (!menu) return;
          if (e.key === "Escape") setMenu(false);
          if (e.key === "Tab") {
            const nodes = Array.from(
              sidebar.current?.querySelectorAll<HTMLElement>("a,button") || [],
            ).filter(
              (el) =>
                el.getClientRects().length > 0 &&
                el.checkVisibility() &&
                !el.hasAttribute("disabled"),
            );
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
              <img src="/avatar-icon.svg" width="44" height="44" alt="" />
            </span>
            <div>
              AVATAR<small>ÜRETİM VE STOK YÖNETİMİ</small>
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
          <span className="workspace-dot" /> AVATAR{" "}
          <span>Çalışma alanı</span>
        </div>
        <nav>
          {navigation.map((group, i) => (
            <section className="nav-group" key={group.label}>
              <button
                className="nav-group-toggle"
                aria-expanded={openGroups.includes(group.label)}
                aria-controls={"nav-group-" + i}
                onClick={() =>
                  setOpenGroups((groups) =>
                    groups.includes(group.label)
                      ? groups.filter((g) => g !== group.label)
                      : [...groups, group.label],
                  )
                }
              >
                <span>{group.label}</span>
                <ChevronRight
                  size={16}
                  className={openGroups.includes(group.label) ? "expanded" : ""}
                />
              </button>
              <div
                id={"nav-group-" + i}
                hidden={!openGroups.includes(group.label)}
              >
                {group.items.map((x) => {
                  const active = matchesEntry(
                    x.path,
                    location.pathname,
                    location.search,
                  );
                  return (
                    <NavLink
                      to={x.path}
                      key={x.path}
                      className={"nav-item " + (active ? "active" : "")}
                      aria-current={active ? "page" : false}
                      onClick={() => setMenu(false)}
                    >
                      <x.icon size={18} />
                      <span>{x.label}</span>
                      {active && <ChevronRight size={14} />}
                    </NavLink>
                  );
                })}
              </div>
            </section>
          ))}
        </nav>
        <div className="sidebar-footer">
          <LockKeyhole size={17} />
          <div>
            Yerel çalışma alanı<small>AVATAR</small>
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
            <button id="apk-download-trigger" className="button primary apk-download-trigger" type="button"
              aria-haspopup="dialog" onClick={() => setApkOpen(true)}>
              <Smartphone size={18} aria-hidden="true" />Android Uygulamasını İndir
            </button>
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
              location.pathname.startsWith("/belgeler/satis/")
                ? location.pathname.endsWith("/duzenle")
                  ? "Taslak düzenle"
                  : "Belge görüntüle"
                : detail
                  ? ({ Satışlar: "Satış", "Dış üretim": "Üretim emri" }[
                      title
                    ] || title) + " ayrıntısı"
                  : title
            }
            description={module?.description}
            action={
              <div className="page-actions">
                {detail && module && (
                  <NavLink className="text-button" to={module.path}>
                    Listeye dön
                  </NavLink>
                )}
                {!detail && module && "action" in module && (
                  <a className="button primary" href="#create-record">
                    {module.action}
                  </a>
                )}
                <button
                  className="button refresh"
                  onClick={() => void client.invalidateQueries()}
                  disabled={!!fetching}
                >
                  <RefreshCw size={16} className={fetching ? "spin" : ""} />
                  Yenile
                </button>
              </div>
            }
          />
          <Suspense fallback={<State loading>{null}</State>}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/uyarilar" element={<Alerts />} />
              <Route path="/belgeler" element={<Documents />} />
              <Route path="/belgeler/satis/:id/*" element={<SaleDocument />} />
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
            <span>AVATAR</span>
            <span>Kayıtlı lotlar. Gerçek maliyetler.</span>
          </footer>
        </main>
      </div>
      {apkOpen && <Suspense fallback={null}><ApkDownloadDialog onClose={() => setApkOpen(false)} /></Suspense>}
    </div>
  );
}
