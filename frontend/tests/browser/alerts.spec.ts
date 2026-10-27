import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {api} from './fixtures';
import type {Alert,AlertPage,AlertEvaluation} from '../../src/lib/alerts';
const seed=JSON.parse(readFileSync(process.env.AVATAR_ALERT_DEMO_SEED||'/tmp/avatar-task17-seed.json','utf8')) as {
  near_lot_id:string;blocked_lot_id:string;expired_lot_id:string;recall_id:string;product_id:string;operation_id:string;prediction_id:string;
};

test('gerçek MySQL uyarıları, severity filtresi ve lot detayı; bütün tarayıcı akışı salt GET',async({page,request})=>{
  const posts:string[]=[];page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/api/v1/'))posts.push(r.url());});
  const current=await api<AlertPage>(request,'/alerts');expect(current.summary).toMatchObject({total:6,critical:2,warning:4});
  await page.goto('/uyarilar');await expect(page.getByRole('heading',{name:'Güncel uyarı listesi',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Uyarıyı incele',exact:true})).toHaveCount(6);
  await page.getByLabel('Öncelik',{exact:true}).selectOption('critical');
  await expect(page.getByRole('button',{name:'Uyarıyı incele',exact:true})).toHaveCount(2);
  await page.getByLabel('Kural türü',{exact:true}).selectOption('LOT_BLOCKED_STOCK');
  await expect(page.getByRole('button',{name:'Uyarıyı incele',exact:true})).toHaveCount(1);
  await page.getByRole('button',{name:'Uyarıyı incele',exact:true}).click();
  const dialog=page.getByRole('dialog');await expect(dialog).toContainText('Bloke stok');await expect(dialog).toContainText('0 paket');
  const alert=current.items.find(row=>row.rule_code==='LOT_BLOCKED_STOCK')!;
  expect(alert.source_id).toBe(seed.blocked_lot_id);expect(alert.evidence.related_recalls?.[0].recall_id).toBe(seed.recall_id);
  await dialog.getByRole('link',{name:'Lot kaydını incele',exact:true}).click();await expect(page).toHaveURL('/izlenebilirlik?lot='+seed.blocked_lot_id);
  await expect(page.getByRole('heading',{name:'Kaynak lotun ileri kayıt zinciri',exact:true})).toBeVisible();expect(posts).toEqual([]);
});

test('kayıtlı tahmin–kesin gerçekleşme, sentetik köken, açık eşik ve gerçek operasyon bağlantısı',async({page,request})=>{
  const result=await api<AlertPage>(request,'/alerts?rule_code=PRODUCTION_EKP_DEVIATION&operation_id='+seed.operation_id);
  expect(result.items).toHaveLength(1);expect(result.items[0].evidence.prediction_id).toBe(seed.prediction_id);
  expect(result.items[0].observed_value).toBe('38.587500');
  await page.goto('/uyarilar?rule_code=PRODUCTION_EKP_DEVIATION&operation_id='+seed.operation_id);
  await page.getByRole('button',{name:'Uyarıyı incele',exact:true}).click();const dialog=page.getByRole('dialog');
  await expect(dialog).toContainText('Tahmin–gerçekleşme karşılaştırması · SYNTHETIC');
  await expect(dialog).toContainText('Kurgusal/demo inceleme eşiği');await expect(dialog).toContainText('38,5875 EUR/paket');
  await expect(dialog).toContainText('67 kg');
  await dialog.getByRole('link',{name:'Kesin işlemi incele',exact:true}).click();await expect(page).toHaveURL('/uretim/'+seed.operation_id);
  await expect(page.getByText('KURGUSAL-ALERT-URETIM-001',{exact:true}).first()).toBeVisible();
});

test('düşük stok gerçek ürün filtresine gider; boş bilgi filtresi ve gerçek API401',async({page,request})=>{
  await page.goto('/uyarilar?rule_code=LOW_AVAILABLE_STOCK');await page.getByRole('button',{name:'Uyarıyı incele',exact:true}).click();
  const dialog=page.getByRole('dialog');await expect(dialog).toContainText('2 kg');await expect(dialog).toContainText('5 kg');
  await dialog.getByRole('link',{name:'Ürün stoklarını incele',exact:true}).click();
  await expect(page.getByLabel('Ürün',{exact:true})).toHaveValue(seed.product_id);
  await page.goto('/uyarilar?severity=info');await expect(page.getByText(/Bu filtrede güncel uyarı yok/)).toBeVisible();
  await expect(page.getByRole('button',{name:'Uyarıyı incele',exact:true})).toHaveCount(0);
  const response=await request.get((process.env.AVATAR_E2E_API_URL||'http://127.0.0.1:8008')+'/v1/alerts');expect(response.status()).toBe(401);
});

test('390/768/1440px uyarı merkezi erişilebilir; dashboard küçük gerçek özet gösterir',async({page,request})=>{
  const {default:AxeBuilder}=await import('@axe-core/playwright');
  const before=await api<AlertEvaluation>(request,'/alerts/summary');
  for(const width of [390,768,1440]) {
    await page.setViewportSize({width,height:900});await page.goto('/uyarilar');
    await expect(page.getByRole('button',{name:'Uyarıyı incele',exact:true})).toHaveCount(6);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    const results=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
    expect(results.violations.map(row=>({id:row.id,impact:row.impact,targets:row.nodes.map(node=>node.target)}))).toEqual([]);
    await page.screenshot({path:'/tmp/avatar-task17-alerts-'+width+'.png',fullPage:true});
  }
  await page.goto('/');await expect(page.getByRole('heading',{name:'Güncel operasyonel uyarılar',exact:true})).toBeVisible();
  await expect(page.getByRole('link',{name:'Uyarı merkezini aç',exact:true})).toBeVisible();
  const after=await api<AlertEvaluation>(request,'/alerts/summary');expect(after.summary).toEqual(before.summary);
});
