import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import QRCode from "qrcode";
import { Check, Copy, RefreshCw, ShieldCheck, Wifi } from "lucide-react";
import { DetailDrawer } from "../../components/dialogs";
import { fetchShareStatus } from "./status";

export function LocalQr({ url }: { url: string }) {
  const qr = useMemo(() => {
    const { modules } = QRCode.create(url, { errorCorrectionLevel: "M" });
    const commands: string[] = [];
    for (let y = 0; y < modules.size; y++)
      for (let x = 0; x < modules.size; x++)
        if (modules.get(y, x)) commands.push(`M${x + 4},${y + 4}h1v1h-1z`);
    return { size: modules.size + 8, path: commands.join("") };
  }, [url]);
  return <svg className="apk-qr" role="img" aria-label="Geçerli APK indirme bağlantısının QR kodu"
    viewBox={`0 0 ${qr.size} ${qr.size}`} width="256" height="256" shapeRendering="crispEdges">
    <rect width="100%" height="100%" fill="#fff" /><path d={qr.path} fill="#000" />
  </svg>;
}

const messages = {
  inactive: "APK paylaşımı henüz başlatılmadı.",
  used: "Bu bağlantı kullanıldı. Yeni indirme için paylaşımı yeniden başlatın.",
  expired: "Paylaşımın süresi doldu. Yeni indirme için paylaşımı yeniden başlatın.",
  local_only: "Paylaşım yalnız bu bilgisayarda açık. Telefon için Wi-Fi IPv4 adresiyle yeniden başlatın.",
  unavailable: "APK paylaşımı doğrulanamadı. Yerel aracı ve dosya izinlerini kontrol edin.",
};

export default function ApkDownloadDialog({ onClose }: { onClose: () => void }) {
  const query = useQuery({ queryKey: ["apk-share"], queryFn: ({ signal }) => fetchShareStatus(signal),
    retry: false, gcTime: 0, staleTime: 0, refetchInterval: 1000, refetchOnWindowFocus: true });
  const [now, setNow] = useState(Date.now()), [copied, setCopied] = useState(false), [copyError, setCopyError] = useState(false), [lastExpiry, setLastExpiry] = useState<number | null>(null);
  const data = query.isError ? undefined : query.data;
  const share = data?.state === "active" && data.expiresAt > now ? data : undefined;
  const state = data?.state === "active" ? "expired" : data?.state || "inactive";
  const statusMessage = query.isPending ? "Yerel paylaşım kontrol ediliyor…"
    : query.isError ? "Yerel APK paylaşımına erişilemiyor. Aracı ve web bağlantısını kontrol edin."
    : state === "inactive" && lastExpiry !== null
      ? now >= lastExpiry ? messages.expired : "Paylaşım sona erdi. Yeni indirme için yerel aracı yeniden başlatın."
      : messages[state];
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => { if (share) setLastExpiry(share.expiresAt); }, [share]);
  useEffect(() => { setCopied(false); setCopyError(false); }, [share?.url]);
  async function copy() {
    if (!share || Date.now() >= share.expiresAt) return;
    try { await navigator.clipboard.writeText(share.url); setCopied(true); setCopyError(false); }
    catch { setCopyError(true); }
  }
  return <DetailDrawer title="Android Uygulamasını İndir" onClose={onClose} className="apk-download-dialog">
    <div className="apk-brand"><img src="/avatar-icon.svg" alt="" width="56" height="56" />
      <div><h3>AVATAR Preview</h3><p>Güvenilir ağınızda tek kullanımlık indirme</p></div></div>
    <p className="apk-network"><Wifi size={20} aria-hidden="true" /> Telefonunuz bilgisayarla aynı güvenilir Wi-Fi ağında olmalı.</p>
    {share ? <>
      <div className="apk-share-grid">
        <div className="apk-qr-panel"><LocalQr url={share.url} /><p>Telefon kamerasıyla okutun.<br />Standart tarayıcınızla indirin.</p></div>
        <div className="apk-metadata">
          <span className="apk-status active"><span aria-hidden="true">●</span> İndirmeye hazır</span>
          <dl><div><dt>Sürüm</dt><dd>{share.version}</dd></div>
            <div><dt>Dosya boyutu</dt><dd>{new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(share.bytes / 1024 / 1024)} MiB <small>({share.bytes.toLocaleString("tr-TR")} bayt)</small></dd></div>
            <div><dt>Kalan geçerlilik</dt><dd data-testid="apk-countdown">{Math.max(0, Math.ceil((share.expiresAt - now) / 1000))} saniye</dd></div>
            <div><dt>SHA256</dt><dd className="apk-hash">{share.sha256}</dd></div></dl>
        </div>
      </div>
      <label className="apk-url-label">Geçici indirme bağlantısı
        <input className="apk-share-url" value={share.url} readOnly spellCheck={false} autoComplete="off" aria-describedby="apk-link-help" />
      </label>
      <p id="apk-link-help" className="apk-help">Bu bağlantı gizlidir. Bir indirmeden veya süre bitiminden sonra kullanılamaz.</p>
      <button type="button" className="button primary" onClick={() => void copy()}>
        {copied ? <Check size={18} /> : <Copy size={18} />}{copied ? "Bağlantı kopyalandı" : "İndirme bağlantısını kopyala"}
      </button>
      {copyError && <p role="alert">Kopyalanamadı. Yukarıdaki bağlantıyı seçip elle kopyalayabilirsiniz.</p>}
    </> : <div className="apk-empty" role="status">
      <ShieldCheck size={32} aria-hidden="true" />
      <p>{statusMessage}</p>
      <p>Geçerli bir paylaşım olmadan QR kodu oluşturulmaz.</p>
    </div>}
    <div className="apk-footer-actions"><button className="button" type="button" onClick={() => void query.refetch()} disabled={query.isFetching}>
      <RefreshCw size={16} />Paylaşımı kontrol et</button><span className="apk-help">Yeni bağlantıyı yalnız yerel operatör başlatabilir.</span></div>
    {!share && <section className="apk-start-help" aria-label="Güvenli başlatma adımları">
      <h3>Bilgisayarda paylaşımı başlatın</h3>
      <ol><li>Güncel Preview APK'yı derleyin ve SHA256 değerini doğrulayın.</li>
        <li>Bilgisayarınızın Wi-Fi IPv4 adresini kullanarak repo kökünde aşağıdaki komutu çalıştırın.</li>
        <li>Bu pencere paylaşımı otomatik algılar. Başka indirme için aracı yeniden çalıştırın.</li></ol>
      <pre><code>{"python3 tools/share_apk.py \\\n  --sha256 DOGRULANMIS_64_HANELI_SHA256 \\\n  --bind WIFI_IPV4_ADRESINIZ --allow-lan --ttl 180"}</code></pre>
      <p className="apk-help">Adres örneği: 192.168.1.10. 127.0.0.1 / localhost telefon içindir, bilgisayara ulaşmaz. Docker kurulumu için docs/INDIRME.md içindeki yerel soket adımını uygulayın.</p>
    </section>}
    <p className="apk-safety">HTTP aktarımı şifrelenmez; yalnız güvenilir ağda kullanın. Bu işlem yalnız APK indirir. Sunucu eşleştirmesi yapmaz; API anahtarınızı paylaşmayın. Eski uygulamanızı kaldırmayın veya verisini silmeyin.</p>
  </DetailDrawer>;
}
