import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, expect, it, vi } from 'vitest';
import { AlertDetail, DashboardAlerts } from '../src/components/Alerts';
import { Alerts } from '../src/pages/Alerts';
import type { Alert, AlertPage } from '../src/lib/alerts';

const id='00000000-0000-5000-8000-000000000017';
const lot='00000000-0000-4000-8000-000000000001';
const base:Alert={id,rule_code:'EXPIRY_PAST',severity:'critical',source_type:'lot',source_id:lot,source_label:'KURGUSAL ET · LOT-1',location_id:lot,
  title:'Son tüketim tarihi geçmiş',message:'Kayıtlı SKT dün geçti.',observed_value:'-1',threshold_value:'0',unit:'day',threshold_unit:'day',threshold_origin:'configured_review_window',
  evaluated_at:'2026-10-28T00:01:00+03:00',policy_version:'ek02-v1',policy_fingerprint:'version',recommended_action:'Lot kaydını inceleyin.',
  related_links:[{label:'Lot kaydını incele',href:'/izlenebilirlik?lot='+lot}],
  evidence:{lot_code:'LOT-1',physical_quantity:'2.000000',available_quantity:'0.000000',quantity_unit:'kg',location_name:'KURGUSAL karantina',location_kind:'quarantine',expires_at:'2026-10-27',days_remaining:-1}};
const page:AlertPage={items:[base],next_cursor:null,summary:{total:1,critical:1,warning:0,info:0,by_rule:{EXPIRY_PAST:1}},
  evaluated_at:base.evaluated_at,policy:{version:'v1',fingerprint:'f',timezone:'Europe/Istanbul',expiry_days:7,deviation_origin:'demo',cost_percent:'15',yield_percent:'15'},
  diagnostics:{},history_persisted:false};
function wrapper(children:React.ReactNode) {
  return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter>{children}</MemoryRouter></QueryClientProvider>);
}
afterEach(()=>vi.unstubAllGlobals());
it('lot kimliği, karantina ve sıfır kullanılabilir miktarı gerçek alanlardan gösterir',()=>{
  wrapper(<AlertDetail alert={Object.freeze(base)} />);
  expect(screen.getByText('Karantina · satılabilir değil')).toBeVisible();
  expect(screen.getByText('0 kg')).toBeVisible();expect(screen.getByText(/1 gün geçti/)).toBeVisible();
  expect(screen.getByRole('link',{name:'Lot kaydını incele'})).toHaveAttribute('href','/izlenebilirlik?lot='+lot);
  screen.getAllByText(lot,{exact:true}).forEach(node=>expect(node).not.toBeVisible());expect(base.observed_value).toBe('-1');
});
it('model farkını sentetik karşılaştırma olarak sunar; yeni AI yargısı veya fire kararı üretmez',()=>{
  wrapper(<AlertDetail alert={{...base,rule_code:'YIELD_DEVIATION',severity:'warning',source_type:'operation',predicted_value:'0.88',observed_value:'0.7',difference_value:'-0.18',deviation_percent:'25.714286',unit:'kg/kg',threshold_unit:'%',threshold_value:'15',threshold_origin:'demo',
    evidence:{data_origin:'SYNTHETIC',model_version:'ridge-recorded',prediction_limitations:['Gerçek işletme doğruluğu kanıtlanmadı.'],explained_difference_kg:'3',percentage_denominator:'abs(actual)'}}} />);
  expect(screen.getByText(/Tahmin–gerçekleşme karşılaştırması · SYNTHETIC/)).toBeVisible();
  expect(screen.getByText('ridge-recorded')).toBeVisible();expect(screen.getByText(/Kurgusal\/demo inceleme eşiği/)).toBeVisible();
  expect(screen.getByText(/açıklanmış miktar farkı tek başına anomali değildir/)).toBeVisible();
  expect(screen.getByText('3 kg',{exact:true})).toBeVisible();
});
it('dashboard gerçek özet gelmeden sıfır sayı veya sahte sonuç göstermez',async()=>{
  const fetch=vi.fn().mockResolvedValue(Response.json({error:{code:'DATABASE_UNAVAILABLE'}},{status:503}));vi.stubGlobal('fetch',fetch);
  wrapper(<DashboardAlerts/>);expect(await screen.findByRole('alert')).toBeVisible();
  expect(screen.queryByText(/0 kritik/)).not.toBeInTheDocument();
  expect(screen.getByRole('link',{name:'Uyarı merkezini aç'})).toHaveAttribute('href','/uyarilar');
});
it('liste ve detay yalnız GET kullanır; filtreler sunucuya gider ve tek sayfa yüklenir',async()=>{
  const fetch=vi.fn().mockImplementation(async(url:string)=>Response.json(url.includes('/alerts/'+id)?base:page));vi.stubGlobal('fetch',fetch);
  wrapper(<Alerts/>);
  expect(await screen.findByText(base.source_label,{exact:true})).toBeVisible();
  await userEvent.setup().selectOptions(screen.getByLabelText('Öncelik'),'critical');
  await waitFor(()=>expect(fetch.mock.calls.some(([url])=>String(url).includes('severity=critical'))).toBe(true));
  await userEvent.setup().click(screen.getByRole('button',{name:'Uyarıyı incele'}));
  expect(await screen.findByRole('dialog')).toHaveTextContent('Kayıtlı SKT dün geçti.');
  expect(fetch.mock.calls.some(([url])=>String(url)==='/api/v1/alerts/'+id)).toBe(true);
  expect(fetch.mock.calls.every(([,options])=>!options?.method||options.method==='GET')).toBe(true);
  expect(fetch.mock.calls.filter(([url])=>String(url).includes('cursor='))).toHaveLength(0);
});
it('boş veride uyarı veya işlem uydurmaz',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(Response.json({...page,items:[],summary:{total:0,critical:0,warning:0,info:0,by_rule:{}}})));
  wrapper(<Alerts/>);expect(await screen.findByText(/Bu filtrede güncel uyarı yok/)).toBeVisible();
  expect(screen.queryByRole('button',{name:'Uyarıyı incele'})).not.toBeInTheDocument();
});
it('sayı ve birimi eşikle birlikte gösterir; tarayıcı stok hesabı yapmaz',async()=>{
  const row={...base,rule_code:'LOW_AVAILABLE_STOCK' as const,observed_value:'2.000001',threshold_value:'5',unit:'kg',threshold_unit:'kg',threshold_origin:'demo' as const};
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(Response.json({...page,items:[row]})));
  wrapper(<Alerts/>);expect(await screen.findByText('2,000001 kg')).toBeVisible();expect(screen.getByText('Eşik: 5 kg')).toBeVisible();
});


it('sapma satırında backend yüzdesini yüzde eşiğiyle eşleştirir; gerçek metrik ayrı kalır',async()=>{
  const row={...base,rule_code:'PRODUCTION_EKP_DEVIATION' as const,observed_value:'38.587500',predicted_value:'18.000000',deviation_percent:'53.352770',threshold_value:'15',unit:'EUR/package',threshold_unit:'%',threshold_origin:'demo' as const};
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(Response.json({...page,items:[row]})));
  wrapper(<Alerts/>);expect(await screen.findByText('53,35277 % sapma')).toBeVisible();
  expect(screen.getByText('Gerçek: 38,5875 EUR/paket')).toBeVisible();expect(screen.getByText('Eşik: 15 %')).toBeVisible();
});
