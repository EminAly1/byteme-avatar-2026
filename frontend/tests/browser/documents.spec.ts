import { test, expect, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { api } from './fixtures';
import type { DocumentSource } from '../../src/lib/documents';
declare global { interface Window { documentBeforePrintCount?: number } }

const seed=JSON.parse(readFileSync(process.env.AVATAR_DOCUMENT_DEMO_SEED||'/tmp/avatar-task18-seed.json','utf8')) as Record<string,string>;
function parsePdf(path:string) {
  return JSON.parse(execFileSync(process.env.AVATAR_PDF_PYTHON||fileURLToPath(new URL('../../../backend/.venv/bin/python',import.meta.url)),['-c',
    'import json,sys;from pypdf import PdfReader;r=PdfReader(sys.argv[1],strict=True);print(json.dumps({"pages":len(r.pages),"text":"\\n".join(p.extract_text() for p in r.pages),"sizes":[[float(p.mediabox.width),float(p.mediabox.height)] for p in r.pages]}))',path],{encoding:'utf8'})) as {pages:number;text:string;sizes:number[][]};
}
async function downloadPdf(page:Page,name:string) {
  const downloadEvent=page.waitForEvent('download');
  const responseEvent=page.waitForResponse(r=>r.url().endsWith('/document-drafts/proforma/pdf')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'PDF indir',exact:true}).click();
  const [download,response]=await Promise.all([downloadEvent,responseEvent]);
  expect(response.status()).toBe(200);expect(response.headers()['content-type']).toBe('application/pdf');
  expect(response.headers()['cache-control']).toBe('no-store');
  const path='/tmp/avatar-task18-'+name+'.pdf';await download.saveAs(path);
  expect(readFileSync(path).subarray(0,5).toString()).toBe('%PDF-');
  return {download,pdf:parsePdf(path)};
}

test('gerçek satıştan belge; Türkçe PDF indir ve ayrı gerçek yazdırma akışı',async({page,request})=>{
  const s=await api<DocumentSource>(request,'/document-drafts/sales/'+seed.active_sale_id);
  let pdfPosts=0;const otherWrites:string[]=[];
  page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/api/v1/')){if(r.url().endsWith('/document-drafts/proforma/pdf'))pdfPosts++;else otherWrites.push(r.url());}});
  await page.goto('/belgeler');await expect(page.getByRole('heading',{name:'Belge için satış seçin',exact:true})).toBeVisible();
  await page.locator('a[href="/belgeler/satis/'+s.sale_id+'"]').click();
  const sheet=page.getByRole('article',{name:'A4 belge önizlemesi'});
  await expect(sheet).toContainText(s.customer.name);await expect(sheet).toContainText(s.lines[0].lot_code);
  await page.getByRole('link',{name:'Taslak düzenle',exact:true}).click();
  await page.getByLabel(/^Satıcı unvanı/).fill('KURGUSAL İğde Gıda');
  await page.getByLabel(/^Özel not/).fill('Türkçe karakterler: ğ ü ş ı İ ö ç');
  await page.getByLabel('Kurgusal demo belgesi (kullanıcı beyanı)',{exact:true}).check();
  await page.getByRole('button',{name:'Değişiklikleri bu görünümde uygula'}).click();
  const {download,pdf}=await downloadPdf(page,'browser-active');
  expect(download.suggestedFilename()).toBe('proforma-'+s.sale_id+'.pdf');
  expect(pdf.text).toContain('ğ ü ş ı İ ö ç');expect(pdf.text).toContain('750,00 EUR');
  expect(pdf.text).toContain('RESMÎ FATURA DEĞİLDİR');expect(pdf.text).toContain(s.shipments[0].id);
  expect(pdf.text).not.toContain('Brüt kâr');expect(pdf.text).not.toContain('Tüketim maliyeti');
  for(const [w,h] of pdf.sizes){expect(w).toBeCloseTo(595.2756,2);expect(h).toBeCloseTo(841.8898,2);}
  await page.evaluate(()=>{window.documentBeforePrintCount=0;addEventListener('beforeprint',()=>{window.documentBeforePrintCount=(window.documentBeforePrintCount||0)+1;});});
  await page.getByRole('button',{name:'Önizle',exact:true}).click();
  await expect(page.getByRole('dialog').getByText(/sayfalı PDF hazır/)).toBeVisible({timeout:60000});
  await page.getByRole('dialog').getByRole('button',{name:'Yazdır',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>window.documentBeforePrintCount)).toBeGreaterThan(0);
  expect(pdfPosts).toBe(2);expect(otherWrites).toEqual([]);
  await page.emulateMedia({media:'print'});
  await expect(page.locator('.sidebar')).not.toBeVisible();await expect(page.locator('.document-editor')).not.toBeVisible();
  const printed='/tmp/avatar-task18-browser-print.pdf';await page.pdf({path:printed,format:'A4',preferCSSPageSize:true,printBackground:true});
  const printPdf=parsePdf(printed);expect(printPdf.text).toContain('ğ ü ş ı İ ö ç');
  expect(printPdf.text).not.toContain('PDF indir');expect(printPdf.text).not.toContain('Taslak ayarları');
  expect(await api<DocumentSource>(request,'/document-drafts/sales/'+s.sale_id)).toEqual(s);
});

test('gerçek kısmi/tam iade ve iptal ayrı gösterilir; 45 kalemli gerçek PDF sayfalanır',async({page,request})=>{
  for(const [key,state] of [['partial_sale_id','Kısmi iade'],['returned_sale_id','Tam iade'],['cancelled_sale_id','İptal edilmiş satış']]) {
    await page.goto('/belgeler/satis/'+seed[key]);const sheet=page.getByRole('article',{name:'A4 belge önizlemesi'});
    await expect(sheet.locator('.document-source-state')).toContainText(state);
    if(key!=='partial_sale_id')await expect(sheet.locator('.document-source-state')).toContainText('GÜNCEL ÖDEME TALEBİ DEĞİLDİR');
  }
  await page.getByRole('link',{name:'Taslak düzenle',exact:true}).click();
  await page.getByLabel('Belge görünümü',{exact:true}).selectOption('sale_summary');
  await page.getByLabel('Kurgusal demo belgesi (kullanıcı beyanı)',{exact:true}).check();
  await page.getByRole('button',{name:'Değişiklikleri bu görünümde uygula'}).click();
  const cancelled=await downloadPdf(page,'browser-cancelled');
  expect(cancelled.pdf.text).toContain('SATIŞ ÖZETİ — MALİ BELGE DEĞİLDİR');
  expect(cancelled.pdf.text).toContain('GÜNCEL ÖDEME TALEBİ DEĞİLDİR');
  const s=await api<DocumentSource>(request,'/document-drafts/sales/'+seed.long_sale_id);expect(s.lines).toHaveLength(45);expect(s.shipments).toHaveLength(2);
  await page.goto('/belgeler/satis/'+s.sale_id);await expect(page.locator('.document-lines tbody tr')).toHaveCount(45);
  await page.getByRole('link',{name:'Taslak düzenle',exact:true}).click();
  await page.getByLabel(/^Özel not/).fill('Son satır sonrası Türkçe: ğ ü ş ı İ ö ç');
  await page.getByLabel('Kurgusal demo belgesi (kullanıcı beyanı)',{exact:true}).check();
  await page.getByRole('button',{name:'Değişiklikleri bu görünümde uygula'}).click();
  const long=await downloadPdf(page,'browser-long');expect(long.pdf.pages).toBeGreaterThan(1);
  for(const row of s.lines)expect(long.pdf.text).toContain(row.lot_code);
  expect(long.pdf.text).toContain('138,60 EUR');expect(long.pdf.text).toContain('Son satır sonrası Türkçe: ğ ü ş ı İ ö ç');
});

test('390px ve masaüstü belge önizlemesi; güvenli gerçek 404/401 ve kaynak satış bağlantısı',async({page,request})=>{
  const {default:AxeBuilder}=await import('@axe-core/playwright');
  for(const width of [390,1440]) {
    await page.setViewportSize({width,height:900});await page.goto('/belgeler/satis/'+seed.active_sale_id);
    await expect(page.getByRole('article',{name:'A4 belge önizlemesi'})).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
    expect(result.violations.map(row=>({id:row.id,targets:row.nodes.map(n=>n.target)}))).toEqual([]);
    await page.screenshot({path:'/tmp/avatar-task18-documents-'+width+'.png',fullPage:true});
  }
  await page.getByRole('link',{name:'Kaynak satışa dön',exact:true}).click();
  await expect(page.getByRole('link',{name:'Belge taslağı oluştur',exact:true})).toHaveAttribute('href','/belgeler/satis/'+seed.active_sale_id);
  await page.goto('/belgeler/satis/00000000-0000-4000-8000-000000000000');
  await expect(page.getByRole('alert')).toBeVisible();await expect(page.getByRole('button',{name:'PDF indir',exact:true})).toHaveCount(0);
  const unauth=await request.get((process.env.AVATAR_E2E_API_URL||'http://127.0.0.1:8009')+'/v1/document-drafts/sales/'+seed.active_sale_id);
  expect(unauth.status()).toBe(401);
});
