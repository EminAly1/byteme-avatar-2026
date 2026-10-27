import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import type { Alert, AlertEvaluation } from '../lib/alerts';
import { alertRules, alertSeverities, alertUnit } from '../lib/alerts';
import { request } from '../lib/api';
import { amount, dateTime } from '../lib/format';
import { displayDecimal } from '../lib/presentation';
import { Badge, Section, State } from './ui';
import { CriticalNotice, RecordId, ReviewSummary } from './workflow';
export function AlertPriority({ alert }: { alert: Pick<Alert, 'severity'> }) {
  return <Badge tone={alert.severity === 'critical' ? 'red' : alert.severity === 'warning' ? 'amber' : ''}>{alertSeverities[alert.severity]}</Badge>;
}
export function AlertDetail({ alert }: { alert: Alert }) {
  const evidence = alert.evidence;
  return <div className="stack">
    <div><AlertPriority alert={alert} /> <Badge>{alertRules[alert.rule_code]}</Badge></div>
    <h3>{alert.title}</h3><strong>{alert.source_label}</strong><p>{alert.message}</p>
    <ReviewSummary items={[
      ['Gözlenen değer', displayDecimal(alert.observed_value, 6) + ' ' + alertUnit(alert.unit)],
      ['İnceleme eşiği', displayDecimal(alert.threshold_value, 6) + ' ' + alertUnit(alert.threshold_unit)],
      ['Değerlendirme', dateTime(alert.evaluated_at) + ' · Türkiye saati'],
    ]} />
    <p className="caption">{alert.threshold_origin === 'demo' ? 'Kurgusal/demo inceleme eşiği; işletme standardı veya kanıtlanmış anomali sınırı değildir.' : alert.threshold_origin === 'operator_configured' ? 'Eşik açık operatör konfigürasyonundan alınır; otomatik olarak öğrenilmez.' : 'SKT, Europe/Istanbul takvim günü ve yapılandırılmış gün penceresiyle karşılaştırılır.'}</p>
    {evidence.location_name && <ReviewSummary items={[
      ['Kayıtlı konum', evidence.location_name], ['Konum türü', evidence.location_kind === 'quarantine' ? 'Karantina · satılabilir değil' : evidence.location_kind === 'external_producer' ? 'Dış üretici' : 'İşletme deposu'],
      ['Fiziksel kayıtlı miktar', amount(evidence.physical_quantity) + ' ' + alertUnit(evidence.quantity_unit || '')],
      ['Bu değerlendirmede kullanılabilir', amount(evidence.available_quantity) + ' ' + alertUnit(evidence.quantity_unit || '')],
    ]} />}
    {evidence.expires_at && <p>Son tüketim tarihi: <strong>{evidence.expires_at}</strong> · {evidence.days_remaining != null && evidence.days_remaining < 0 ? `${Math.abs(evidence.days_remaining)} gün geçti` : `${evidence.days_remaining} gün kaldı`}.</p>}
    {alert.predicted_value != null && <div className="stack">
      <Badge tone="amber">Tahmin–gerçekleşme karşılaştırması · {evidence.data_origin}</Badge>
      <ReviewSummary items={[
        ['Kayıtlı tahmin', displayDecimal(alert.predicted_value, 6) + ' ' + alertUnit(alert.unit)],
        ['Gerçekleşen', displayDecimal(alert.observed_value, 6) + ' ' + alertUnit(alert.unit)],
        ['İşaretli fark (gerçek − tahmin)', displayDecimal(alert.difference_value, 6)],
        ['Mutlak sapma', displayDecimal(alert.deviation_percent, 6) + ' %'],
        ['Model sürümü', evidence.model_version || 'Bilinmiyor'],
        ['Açıklanmış miktar farkı', amount(evidence.explained_difference_kg) + ' kg'],
      ]} />
      <p className="caption">Yüzde = |gerçek − tahmin| / |gerçek| × 100. Yalnız eşik üstü kayıt gösterilir; açıklanmış miktar farkı tek başına anomali değildir.</p>
      <ul>{evidence.prediction_limitations?.map(text => <li key={text}>{text}</li>)}</ul>
      <p className="caption">Kayıtlı tahmin: {evidence.prediction_recorded_at ? dateTime(evidence.prediction_recorded_at) : 'Bilinmiyor'} · Kesin kapanış: {evidence.posted_at ? dateTime(evidence.posted_at) : 'Bilinmiyor'}.</p>
    </div>}
    <CriticalNotice>{alert.recommended_action} Uyarı otomatik stok, maliyet veya recall işlemi yapmaz.</CriticalNotice>
    <div className="quick-links">{alert.related_links.map(link => <Link className="button" key={link.href} to={link.href}>{link.label}</Link>)}</div>
    <details><summary>Kural ve gerçek kayıt referansları</summary><p>Politika: {alert.policy_version} · {alert.policy_fingerprint}</p>
      <RecordId id={alert.id} label="Kararlı uyarı kimliği" /><RecordId id={alert.source_id} label="Kaynak kayıt" />
      {alert.location_id && <RecordId id={alert.location_id} label="Konum kaydı" />}
      {evidence.prediction_id && <RecordId id={evidence.prediction_id} label="Kayıtlı tahmin" />}
    </details>
  </div>;
}
export function DashboardAlerts() {
  const query = useQuery({ queryKey: ['alerts-summary'], queryFn: ({signal}) => request<AlertEvaluation>('/alerts/summary', {signal}), staleTime: 30000, retry: false });
  return <Section title="Güncel operasyonel uyarılar" action={<Link className="text-button" to="/uyarilar">Uyarı merkezini aç</Link>}>
    <State loading={query.isPending} error={query.error}>{query.data && <div className="alert-dashboard-summary">
      <AlertTriangle size={20} aria-hidden="true" /><p><strong>{query.data.summary.critical}</strong> kritik · <strong>{query.data.summary.warning}</strong> uyarı · <strong>{query.data.summary.total}</strong> toplam</p>
      <small>{dateTime(query.data.evaluated_at)} · Salt okunur güncel değerlendirme</small>
    </div>}</State>
  </Section>;
}
