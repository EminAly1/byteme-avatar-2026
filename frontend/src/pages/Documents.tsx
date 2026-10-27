import { useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Download, FileText, Printer, ArrowLeft, ArrowRight, ShieldCheck } from 'lucide-react';
import { request } from '../lib/api';
import { dateTime, eur, short } from '../lib/format';
import type { Page } from '../lib/types';
import type { Sale } from '../lib/modules';
import { draftLimits, fetchDocumentPdf, initialDraft, saveDocumentPdf, type DocumentKind, type DocumentSource } from '../lib/documents';
import { Empty, ErrorBox, Section, State, Table } from '../components/ui';
import { ModuleIntro } from '../components/workflow';
import { DocumentSheet } from '../components/DocumentSheet';
import './documents.css';

export function Documents() {
  const [cursor,setCursor]=useState('');
  const q=useQuery({queryKey:['document-sales',cursor],queryFn:()=>request<Page<Sale>>('/sales?limit=20'+(cursor?'&cursor='+cursor:'')),retry:false});
  return <div className="stack document-root"><ModuleIntro title="Kesin kayıttan, özenli belgeye." description="Kayıtlı bir satış seçin. Proforma veya satış özeti taslağını inceleyin, PDF indirin ya da yazdırın." icon={<FileText size={24}/>}/>
    <div className="document-boundary"><ShieldCheck size={20}/><div><strong>Belge taslağı, kesin satıştan ayrı.</strong><p>Fiyatlar, miktarlar ve lotlar kaynak kayıttan gelir. Yalnız belge notları düzenlenir. Resmî fatura oluşturulmaz.</p></div></div>
    <Section title="Belge için satış seçin" subtitle="Her seferinde en fazla 20 kayıt. Müşteri, lot ve düzeltmeler seçilen satışın önizlemesinde gösterilir."><State loading={q.isPending} error={q.error}>
      {q.data&&!q.data.items.length?<Empty>Henüz kayıtlı satış yok. Satış kaydı olmadan tutar veya belge uydurulmaz.</Empty>:<Table headers={['Satış tarihi / kaynak','Orijinal kayıtlı tutar','Belge']} empty={false}>{q.data?.items.map(s=><tr key={s.id}><td>{dateTime(s.sold_at)}<small className="code">{short(s.id)}</small></td><td>{eur(s.total_amount)}</td><td><Link className="text-button" to={'/belgeler/satis/'+s.id}>Belge taslağını aç <ArrowRight size={14}/></Link></td></tr>)}</Table>}
      <div className="document-pagination"><button className="button" disabled={!cursor} onClick={()=>setCursor('')}>İlk sayfa</button><button className="button" disabled={!q.data?.next_cursor} onClick={()=>setCursor(q.data?.next_cursor||'')}>Sonraki sayfa</button></div>
    </State></Section></div>;
}

const fields=[['title','Belge başlığı'],['description','Belge açıklaması'],['seller_name','Satıcı unvanı'],['seller_contact','Satıcı iletişim bilgisi'],['reference','Taslak referansı'],['payment_note','Ödeme / vade açıklaması'],['delivery_note','Teslimat açıklaması'],['note','Özel not']] as const;
function Editor({saleId}:{saleId:string}) {
  const q=useQuery({queryKey:['document-source',saleId],queryFn:()=>request<DocumentSource>('/document-drafts/sales/'+saleId),retry:false,refetchOnWindowFocus:false});
  const [draft,setDraft]=useState(initialDraft),[kind,setKind]=useState<DocumentKind>('proforma'),[busy,setBusy]=useState(''),[error,setError]=useState<unknown>(),[notice,setNotice]=useState('');
  const form=useRef<HTMLFormElement>(null);
  async function output(mode:'pdf'|'print') {
    if(!q.data||!form.current?.reportValidity())return;
    setBusy(mode);setError(undefined);setNotice('');
    try {
      if(mode==='pdf') {
        const blob=await fetchDocumentPdf(q.data,kind,draft);saveDocumentPdf(blob,saleId,kind);setNotice('PDF dosyası indirildi. Taslak sunucuda saklanmadı.');
      } else {
        const fresh=await request<DocumentSource>('/document-drafts/sales/'+saleId);
        if(fresh.source_fingerprint!==q.data.source_fingerprint) {await q.refetch();setNotice('Kaynak değişti. Önizleme güncellendi; inceleyip yeniden yazdırın.');return;}
        await document.fonts.ready;window.print();
      }
    } catch(err){setError(err);}finally{setBusy('');}
  }
  return <div className="stack document-root"><div className="document-toolbar"><Link className="text-button" to="/belgeler"><ArrowLeft size={15}/> Belge merkezi</Link><Link className="text-button" to={'/satislar/'+saleId}>Kaynak satışa dön</Link></div>
    <State loading={q.isPending} error={q.error}>{q.data&&<>
      <div className="document-toolbar"><div><h2>{q.data.customer.name}</h2><p className="caption">Geçici taslak — sunucuda saklanmıyor. Sayfadan ayrılınca taslak alanları sıfırlanır.</p></div><div className="document-actions"><button className="button" disabled={!!busy} onClick={()=>void output('print')}><Printer size={17}/>{busy==='print'?'Kaynak kontrol ediliyor…':'Yazdır'}</button><button className="button primary" disabled={!!busy} onClick={()=>void output('pdf')}><Download size={17}/>{busy==='pdf'?'PDF hazırlanıyor…':'PDF indir'}</button></div></div>
      {error?<div className="document-output-error"><ErrorBox error={error}/><button className="button" onClick={()=>{setError(undefined);void q.refetch();}}>Önizlemeyi yenile</button></div>:null}
      {notice&&<p className="notice" role="status">{notice}</p>}
      <div className="document-workspace"><aside className="document-editor" aria-label="Belge taslak ayarları"><Section title="Taslak ayarları" subtitle="Kesin müşteri, satış tarihi, fiyat, miktar ve lot alanları kilitlidir.">
        <form ref={form} className="stack" onSubmit={e=>e.preventDefault()}>
          <fieldset disabled={!!busy} className="document-fields">
          <label>Belge görünümü<select aria-label="Belge görünümü" value={kind} onChange={e=>setKind(e.target.value as DocumentKind)}><option value="proforma">Proforma taslağı</option><option value="sale_summary">Satış özeti</option></select></label>
          <label>Belge düzenleme tarihi<input type="date" required value={draft.document_date} onChange={e=>setDraft({...draft,document_date:e.target.value})}/></label>
          {fields.map(([name,label])=><label key={name}>{label}{['description','seller_contact','payment_note','delivery_note','note'].includes(name)?<textarea rows={name==='note'?4:2} maxLength={draftLimits[name]} value={draft[name]} onChange={e=>setDraft({...draft,[name]:e.target.value})}/>:<input maxLength={draftLimits[name]} value={draft[name]} onChange={e=>setDraft({...draft,[name]:e.target.value})}/>}<small>En fazla {draftLimits[name]} karakter ve 21 satır.{name.startsWith('seller')?' Kullanıcı girişi; doğrulanmadı.':''}</small></label>)}
          <label className="document-demo-toggle"><input type="checkbox" checked={draft.demo} onChange={e=>setDraft({...draft,demo:e.target.checked})}/> Kurgusal demo belgesi (kullanıcı beyanı)</label>
          </fieldset>
        </form>
      </Section></aside><section className="document-preview" aria-label="Belge önizleme alanı"><div className="document-preview-caption"><span>A4 · 210 × 297 mm · EUR</span><span>Ekrana uyarlanmış önizleme</span></div><DocumentSheet source={q.data} kind={kind} draft={draft}/></section></div>
    </>}</State></div>;
}
export function SaleDocument(){const {id=''}=useParams();return <Editor key={id} saleId={id}/>;}
