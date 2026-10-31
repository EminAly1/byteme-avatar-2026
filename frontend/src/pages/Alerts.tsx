import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BellRing } from 'lucide-react';
import { z } from 'zod';
import { request } from '../lib/api';
import type { Alert, AlertPage } from '../lib/alerts';
import { alertRules, alertSeverities, alertUnit } from '../lib/alerts';
import { dateTime } from '../lib/format';
import { displayDecimal } from '../lib/presentation';
import { AlertDetail, AlertPriority } from '../components/Alerts';
import { Empty, Section, State, Table } from '../components/ui';
import { CriticalNotice, DetailDrawer, ModuleIntro, StatCard } from '../components/workflow';

export function Alerts() {
  const [search, setSearch] = useSearchParams();
  const severity = search.get('severity') || '', rule = search.get('rule_code') || '';
  const lot = search.get('lot_id') || '', operation = search.get('operation_id') || '', cursor = search.get('cursor') || '';
  const [sourceKind, setSourceKind] = useState(operation ? 'operation' : 'lot');
  const [sourceId, setSourceId] = useState(lot || operation), [filterError, setFilterError] = useState('');
  const selected = search.get('alert') || '';
  const parameters = new URLSearchParams({limit:'20'});
  for (const [key,value] of [['severity',severity],['rule_code',rule],['lot_id',lot],['operation_id',operation],['cursor',cursor]]) if(value) parameters.set(key,value);
  const query = useQuery({ queryKey:['alerts',parameters.toString()], queryFn:({signal})=>request<AlertPage>('/alerts?'+parameters,{signal}), retry:false });
  const detail = useQuery({ queryKey:['alert',selected], queryFn:({signal})=>request<Alert>('/alerts/'+selected,{signal}), enabled:!!selected, retry:false });
  function change(key:string,value:string) { const next=new URLSearchParams(search);next.delete('cursor');next.delete('alert');value ? next.set(key,value) : next.delete(key);setSearch(next); }
  function close() { const next=new URLSearchParams(search);next.delete('alert');setSearch(next); }
  function firstPage() { const next=new URLSearchParams(search);next.delete('cursor');setSearch(next); }
  return <div className="stack alerts-page">
    <ModuleIntro icon={<BellRing size={24}/>} title="Açıklanabilir operasyonel uyarılar."
      description="Mevcut lot, stok ve kapanmış işlem kayıtlarının salt okunur değerlendirmesi. Kalıcı bildirim geçmişi veya otomatik işlem değildir." />
    <Section title="Uyarı filtreleri">
      <div className="filters">
        <label>Öncelik<select aria-label="Öncelik" value={severity} onChange={event=>change('severity',event.target.value)}>
          <option value="">Tümü</option>{Object.entries(alertSeverities).map(([key,label])=><option key={key} value={key}>{label}</option>)}
        </select></label>
        <label>Kural türü<select aria-label="Kural türü" value={rule} onChange={event=>change('rule_code',event.target.value)}>
          <option value="">Tüm kurallar</option>{Object.entries(alertRules).map(([key,label])=><option key={key} value={key}>{label}</option>)}
        </select></label>
        {(lot||operation) && <button className="button" onClick={()=>{const next=new URLSearchParams(search);next.delete('lot_id');next.delete('operation_id');next.delete('cursor');next.delete('alert');setSourceId('');setSearch(next);}}>Kaynak filtresini temizle</button>}
      </div>
      <details><summary>Kaynak lot veya işlem filtresi</summary>
        <form className="form-grid" onSubmit={event=>{event.preventDefault();if(sourceId&&!z.string().uuid().safeParse(sourceId.trim()).success){setFilterError('Kaynak kaydın tam kayıt kimliğini girin.');return;}setFilterError('');const next=new URLSearchParams(search);next.delete('lot_id');next.delete('operation_id');next.delete('cursor');next.delete('alert');if(sourceId.trim())next.set(sourceKind==='lot'?'lot_id':'operation_id',sourceId.trim());setSearch(next);}}>
          <label className="field">Kaynak türü<select aria-label="Kaynak türü" value={sourceKind} onChange={event=>setSourceKind(event.target.value)}><option value="lot">Lot</option><option value="operation">Üretim / parçalama işlemi</option></select></label>
          <div className="field"><label htmlFor="alert-source">Kaynak kayıt kimliği</label><input id="alert-source" value={sourceId} onChange={event=>{setSourceId(event.target.value);setFilterError('');}} autoComplete="off" placeholder="Örn: 00000000-0000-4000-8000-000000000001" aria-invalid={!!filterError} aria-describedby={filterError?'alert-source-help alert-source-error':'alert-source-help'}/><small id="alert-source-help">Lot veya işlem ayrıntılarındaki tam kimliği kopyalayın.</small></div>
          <button className="button" type="submit">Kaynağa göre filtrele</button>
        </form>
        {filterError&&<p id="alert-source-error" role="alert" className="field-error">{filterError}</p>}
        <p className="caption">Lot filtresi lot kaynaklı, işlem filtresi işlem kaynaklı uyarıları sınırlar. Ürün bazlı düşük stok, tek lot stoğu değildir.</p>
      </details>
    </Section>
    <State loading={query.isPending} error={query.error}>{query.data&&<>
      <div className="stat-grid">
        <StatCard label="Kritik" value={query.data.summary.critical}/><StatCard label="Dikkat gerektiren" value={query.data.summary.warning}/><StatCard label="Toplam mevcut uyarı" value={query.data.summary.total}/>
      </div>
      <p className="caption">Aktif filtre kapsamı · {dateTime(query.data.evaluated_at)} · Türkiye saati · Her istekte güncel değerlendirme; teslim edilmiş bildirim geçmişi değildir.</p>
      {Object.entries(query.data.diagnostics).some(([key,value])=>key!=='inspected_predictions'&&value>0)&&<CriticalNotice>
        Bazı eşikler veya tahminler geçerli karşılaştırma üretmedi; bu kaynaklar için uyarı uydurulmadı.
        <details><summary>Değerlendirilemeyen kayıtlar</summary><ul>{Object.entries(query.data.diagnostics).filter(([key,value])=>key!=='inspected_predictions'&&value>0).map(([key,value])=><li key={key}>{({model_unavailable:'Geçerli model paketi yok',invalid_or_incompatible_snapshot:'Tahmin paketi/sürümü/birimi uyumsuz',threshold_unit_mismatch:'Eşik birimi uyuşmuyor',unknown_threshold_products:'Eşik ürünü bulunamadı',zero_actual_denominator:'Gerçek değer sıfır; yüzde hesaplanamadı'}[key]||'Desteklenmeyen karşılaştırma')}: {value}</li>)}</ul></details>
      </CriticalNotice>}
      <Section title="Güncel uyarı listesi" subtitle="Uyarı otomatik blokaj, satış, stok veya maliyet kaydı oluşturmaz.">
        {!query.data.items.length ? <Empty>Bu filtrede güncel uyarı yok. İlgili kayıt veya eşik bulunmadan uyarı oluşturulmaz.</Empty> :
          <Table readonlyReason="Uyarı sunucuda hesaplanır; bu kaydı düzenleme veya silme desteklenmez." headers={['Öncelik / kural','Kaynak ve açıklama','Gözlenen / eşik','İncele']}>
            {query.data.items.map(alert=><tr key={alert.id}>
              <td><AlertPriority alert={alert}/><small>{alertRules[alert.rule_code]}</small></td>
              <td><strong>{alert.source_label}</strong><p>{alert.title}</p><small>{dateTime(alert.evaluated_at)}</small><small>{alert.predicted_value!=null?'Tahmin–gerçekleşme karşılaştırması · sentetik model':'Mevcut kayıtlı stok'}</small></td>
              <td>{alert.deviation_percent != null ? <><strong>{displayDecimal(alert.deviation_percent,6)} % sapma</strong><small>Gerçek: {displayDecimal(alert.observed_value,6)} {alertUnit(alert.unit)}</small></> : <>{displayDecimal(alert.observed_value,6)} {alertUnit(alert.unit)}</>}<small>Eşik: {displayDecimal(alert.threshold_value,6)} {alertUnit(alert.threshold_unit)}</small>{alert.threshold_origin==='demo'&&<small>Kurgusal/demo inceleme eşiği</small>}</td>
              <td><button className="text-button" onClick={()=>{const next=new URLSearchParams(search);next.set('alert',alert.id);setSearch(next);}}>Uyarıyı incele</button></td>
            </tr>)}
          </Table>}
        <div className="quick-links">
          <button className="button" disabled={!cursor} onClick={firstPage}>İlk sayfa</button>
          <button className="button" disabled={!query.data.next_cursor} onClick={()=>{const next=new URLSearchParams(search);next.set('cursor',query.data!.next_cursor!);next.delete('alert');setSearch(next);}}>Sonraki sayfa</button>
          <span className="caption">Sayfada en fazla 20 kayıt; diğer sayfalar tarayıcıya önceden yüklenmez.</span>
        </div>
      </Section>
    </>}</State>
    {query.isError&&cursor&&<button className="button" onClick={firstPage}>Güncel listeyi baştan aç</button>}
    {selected&&<DetailDrawer title="Uyarı incelemesi" onClose={close}><State loading={detail.isPending} error={detail.error}>{detail.data&&<AlertDetail alert={detail.data}/>}</State></DetailDrawer>}
    <p className="caption">Eşikler API sunucusunun açık konfigürasyonundan gelir. Uyarı otomatik muhasebe veya kalite kararı değildir.</p>
  </div>;
}
