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
  BellRing,
  FileText,
  ShieldAlert,
  Sparkles,
  Undo2,
  Ban,
  Repeat2,
} from "lucide-react";
export const navigation = [
  {
    label: "Genel Bakış",
    items: [
      {
        path: "/",
        label: "Genel bakış",
        icon: LayoutDashboard,
        description: "Üretim, stok ve dağıtım kayıtlarını tek yerden yönetin.",
      },
    ],
  },
  {
    label: "Stok ve Alış",
    items: [
      {
        path: "/urunler",
        label: "Ürünler",
        icon: Boxes,
        description: "Hammadde, mamul ve hizmet kartlarını tanımlayın.",
      },
      {
        path: "/is-ortaklari",
        label: "İş ortakları",
        icon: Building2,
        description:
          "Tedarikçi, müşteri ve dış üreticilerin iletişim bilgilerini yönetin.",
        action: "Firma oluştur",
      },
      {
        path: "/depolar",
        label: "Depolar",
        icon: Warehouse,
        description:
          "Kendi depolarınızı ve dış üretici lokasyonlarını tanımlayın.",
        action: "Konum oluştur",
      },
      {
        path: "/alislar",
        label: "Alış ve lot girişi",
        icon: ClipboardList,
        description:
          "Tedarikçiden gelen ürünleri gerçek lot ve maliyetleriyle stoğa alın.",
        action: "Alış kaydet",
      },
      {
        path: "/stoklar",
        label: "Stoklar",
        icon: Layers3,
        description: "Lot ve depo bazında kullanılabilir miktarları inceleyin.",
      },
      {
        path: "/hareketler",
        label: "Depo transferi",
        icon: ArrowLeftRight,
        description:
          "Aynı lotu depolar arasında kayıtlı bir stok hareketiyle taşıyın.",
      },
    ],
  },
  {
    label: "Üretim",
    items: [
      {
        path: "/uretim",
        label: "Dış üretim",
        icon: Factory,
        description:
          "Hammadde sevkini, üretim kapanışını ve gerçek EKP maliyetini takip edin.",
        action: "Dış üretim emri oluştur",
      },
      {
        path: "/parcalama",
        label: "Kuzu parçalama",
        icon: Scissors,
        description:
          "Parçalama girdilerini ve çıktılara dağıtılan maliyeti yönetin.",
      },
      {
        path: "/hareketler?islem=rework",
        label: "Yeniden işleme",
        icon: Repeat2,
        description:
          "Uygun lotları yeniden işleyin; miktar ve maliyet zincirini koruyun.",
      },
    ],
  },
  {
    label: "Satış ve Sevkiyat",
    items: [
      {
        path: "/satislar",
        label: "Satışlar",
        icon: ShoppingBag,
        description:
          "Lot bağlı satışları, kayıtlı gelir ve kârlılığı inceleyin.",
      },
      {
        path: "/sevkiyatlar",
        label: "Sevkiyatlar",
        icon: Truck,
        description:
          "Satışa bağlı ve bağımsız teslimat kayıtlarını takip edin.",
      },
      {
        path: "/dagitimlar",
        label: "İkinci kademe dağıtım",
        icon: Network,
        description:
          "Aracıdan sonraki gerçek alıcı ve lot bağlantılarını kaydedin.",
      },
      {
        path: "/hareketler?islem=iade",
        label: "İade işlemleri",
        icon: Undo2,
        description:
          "Kayıtlı satışa bağlı müşteri iadelerini inceleyin ve oluşturun.",
      },
      {
        path: "/hareketler?islem=iptal",
        label: "Satış iptali",
        icon: Ban,
        description:
          "Kesin kaydı silmeden, uygun satışın ters hareketini kaydedin.",
      },
    ],
  },
  {
    label: "İzlenebilirlik ve Güvenlik",
    items: [
      {
        path: "/izlenebilirlik",
        label: "Lot izlenebilirliği",
        icon: Network,
        description:
          "Bir lotun gerçek kaynaklarını, çıktılarını ve alıcılarını bulun.",
      },
      {
        path: "/geri-cagirma",
        label: "Geri çağırma",
        icon: ShieldAlert,
        description:
          "Etkiyi inceleyin, kapsamı doğrulayın ve kontrollü geri çağırma başlatın.",
      },
      {
        path: "/uyarilar",
        label: "Akıllı uyarı merkezi",
        icon: BellRing,
        description:
          "Kayıtlı operasyonlardan türeyen riskleri ve inceleme önerilerini görün.",
      },
    ],
  },
  {
    label: "Yapay Zekâ ve Analiz",
    items: [
      {
        path: "/yapay-zeka",
        label: "Yapay zekâ tahminleri",
        icon: Sparkles,
        description:
          "Üretim ve parçalama tahminlerini gerçek sonuçlarla karşılaştırın.",
      },
    ],
  },
  {
    label: "Belgeler",
    items: [
      {
        path: "/belgeler",
        label: "Belge merkezi",
        icon: FileText,
        description:
          "Kesin satıştan proforma veya satış özeti hazırlayın; görüntüleyin ve PDF indirin.",
      },
    ],
  },
];
export function matchesEntry(path: string, pathname: string, search: string) {
  const [base, query] = path.split("?");
  if (base === "/hareketler") {
    const operation = pathname.startsWith("/hareketler/rework/")
      ? "rework"
      : new URLSearchParams(search).get("islem");
    return (
      pathname.startsWith(base) &&
      (query
        ? operation === new URLSearchParams(query).get("islem")
        : !operation || operation === "transfer")
    );
  }
  return base === "/"
    ? pathname === "/"
    : pathname === base || pathname.startsWith(base + "/");
}
