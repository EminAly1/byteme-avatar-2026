import { amount, dateTime, eur, units } from '../lib/format';
import { documentLabels, type DocumentKind, type DocumentSource, type DraftFields } from '../lib/documents';

export function DocumentSheet({source:s,kind,draft:d}:{source:DocumentSource;kind:DocumentKind;draft:DraftFields}) {
  return <article className="document-sheet" aria-label="A4 belge önizlemesi">
    <header className="document-masthead">
      <span className="document-symbol" aria-hidden="true"><i/><i/><i/></span>
      <span>TİCARİ BELGE / GEÇİCİ TASLAK</span>
    </header>
    <h2>{d.title || (kind==='proforma'?'Proforma taslağı':'Satış özeti')}</h2>
    <p className="document-disclaimer">{documentLabels[kind]}</p>
    {d.demo&&<p className="document-demo">KURGUSAL DEMO — kullanıcı beyanı</p>}
    <dl className="document-meta"><div><dt>Belge tarihi</dt><dd>{d.document_date||'Girilmedi'}</dd></div><div><dt>Taslak referansı</dt><dd>{d.reference||'Girilmedi'}</dd></div><div><dt>Kesin satış tarihi · Türkiye</dt><dd>{dateTime(s.sold_at)}</dd></div></dl>
    <p className="document-id">Kaynak satış: {s.sale_id}</p>
    {d.description&&<p className="document-text">{d.description}</p>}
    <div className="document-parties">
      <section><h3>Satıcı · kullanıcı taslağı</h3><strong>{d.seller_name||'Satıcı unvanı girilmedi'}</strong><p className="document-text">{d.seller_contact||'İletişim bilgisi girilmedi'}</p><small>Doğrulanmamış, kullanıcı tarafından girilmiş bilgi.</small></section>
      <section><h3>Müşteri · kayıtlı iş ortağı</h3><strong>{s.customer.name}</strong><p className="document-text">{s.customer.contact||'İletişim bilgisi kayıtlı değil'}</p><p className="document-id">Müşteri UUID: {s.customer.id}</p><small>Güncel iş ortağı bilgisi; tarihsel fatura adresi/vergi bilgisi değildir.</small></section>
    </div>
    <h3>Kayıtlı satış kalemleri · orijinal kesin kayıt</h3>
    <table className="document-lines"><colgroup><col style={{width:'43%'}}/><col style={{width:'17%'}}/><col style={{width:'20%'}}/><col style={{width:'20%'}}/></colgroup><thead><tr><th scope="col">Ürün / lot</th><th scope="col">Miktar</th><th scope="col">Birim fiyat</th><th scope="col">Satır toplamı</th></tr></thead><tbody>{s.lines.map(l=><tr key={l.id}><td><strong>{l.line_no}. {l.product_name}</strong><span>Lot: {l.lot_code}</span><small>Lot UUID: {l.lot_id}</small></td><td>{amount(l.quantity)} {units[l.unit]}</td><td>{eur(l.unit_price_eur)}</td><td>{eur(l.total_eur)}</td></tr>)}</tbody></table>
    <section className="document-totals"><h3>Kayıtlı tutarlar · EUR</h3><dl><div><dt>Orijinal kesin satış toplamı</dt><dd>{eur(s.original_total_eur)}</dd></div><div><dt>Kayıtlı iade gelir düzeltmesi</dt><dd>{eur(s.return_credit_eur)}</dd></div><div><dt>Kayıtlı iptal gelir düzeltmesi</dt><dd>{eur(s.cancellation_credit_eur)}</dd></div><div className="document-net"><dt>Düzeltme sonrası kayıtlı satış tutarı</dt><dd>{eur(s.net_after_adjustments_eur)}</dd></div></dl></section>
    <section className="document-status"><h3>Durum: {s.state_label}</h3>{(s.state==='cancelled'||s.state==='returned')?<p><strong>GÜNCEL ÖDEME TALEBİ DEĞİLDİR.</strong> İptal/tam iade orijinal kaydı silmez.</p>:s.state==='partially_returned'?<p>KISMİ İADE: Orijinal satış ve sonraki gelir düzeltmeleri ayrı gösterilmiştir.</p>:null}<p>Tahsilat ve nakit iade durumu kayıtlı değil; ödendi veya ödenecek bakiye beyan edilmez.</p><p>Vergi/KDV bilgisi kayıtlı değil; oran veya dahil/hariç tutar hesaplanmadı.</p></section>
    {s.corrections.map(c=><section className="document-correction" key={c.id}><h3>{c.kind==='return'?'Müşteri iadesi':'Satış iptali'}</h3><p className="document-id">{c.id}</p><p>{dateTime(c.recorded_at)} · {c.reason}</p><p>Kayıtlı gelir düzeltmesi: {eur(c.credit_eur)}</p>{c.lines.map(l=>{const original=s.lines.find(row=>row.id===l.sale_line_id);return <p key={l.sale_line_id}>{original?.product_name} · {original?.lot_code} · {amount(l.quantity)} {units[l.unit]} · {eur(l.credit_eur)}</p>;})}</section>)}
    <section className="document-shipments"><h3>Satışa gerçekten bağlı sevkiyatlar</h3>{!s.shipments.length?<p>Bu satışa bağlı sevkiyat kaydı yok. Bağımsız sevkiyattan fiyat türetilmez.</p>:s.shipments.map(sh=><div key={sh.id}><p className="document-id">{sh.id}</p><p>{dateTime(sh.shipped_at)} · {sh.recipient_name}</p>{sh.lines.map(l=><p key={l.sale_line_id}>{s.lines.find(row=>row.id===l.sale_line_id)?.lot_code} · {amount(l.quantity)} {units[l.unit]}</p>)}</div>)}</section>
    {([['Ödeme / vade açıklaması',d.payment_note],['Teslimat açıklaması',d.delivery_note],['Özel not',d.note]] as const).map(([label,value])=>value&&<section key={label} className="document-note"><h3>{label}</h3><p className="document-text">{value}</p></section>)}
    <footer className="document-footer"><strong>{documentLabels[kind]}</strong><p>Bu belge GİB e-Fatura/e-Arşiv belgesi değildir. Resmî fatura numarası, vergi hesabı veya mali gönderim içermez.</p><p>Geçici taslak — sunucuda saklanmıyor. Taslak düzenlemeleri kesin satış, stok, lot ve maliyet kayıtlarını değiştirmez.</p></footer>
  </article>;
}
