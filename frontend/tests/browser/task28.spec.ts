import { test, expect } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { api, prefix } from "./fixtures";
import type { Product, Party, Location, ReceiptDetail, Stock } from "../../src/lib/types";
const artifact = process.env.AVATAR_E2E_ARTIFACT_DIR || "test-results/task28";
test('P0: gerçek yeni alış drawer, salt-okunur tekrar ve responsive hizalama', async ({ page, request }) => {
  const code=prefix();
  const product=await api<Product>(request,'/products',{sku:code,name:'TEST Bütün kuzu',type:'raw',base_unit:'kg'});
  const supplier=await api<Party>(request,'/parties',{name:code+' TEST tedarikçi',roles:['supplier']});
  const location=await api<Location>(request,'/locations',{name:code+' TEST depo'});
  await page.setViewportSize({width:390,height:900});await page.goto('/alislar');
  await page.getByLabel('Tedarikçi',{exact:true}).selectOption(supplier.id);
  await page.getByLabel('Kabul deposu',{exact:true}).selectOption(location.id);
  await page.getByLabel('Ürün 1',{exact:true}).selectOption(product.id);
  await page.getByLabel('Belge / alış referansı',{exact:true}).fill(code);
  await page.getByLabel('Lot numarası 1',{exact:true}).fill(code+'-LOT');
  await page.getByLabel('Miktar 1',{exact:true}).fill('2,5');
  await page.getByLabel('Toplam maliyet 1 (EUR)',{exact:true}).fill('10');
  await page.getByRole('button',{name:'Alışı kaydet',exact:true}).click();
  const posted=page.waitForResponse(r=>r.url().endsWith('/api/v1/receipts')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Onayla ve kaydet',exact:true}).click();
  const sale=await(await posted).json() as ReceiptDetail;
  const dialog=page.getByRole('dialog',{name:'Alış ayrıntıları'});await expect(dialog).toBeVisible();
  await expect(dialog).toContainText(code+'-LOT'); await expect(dialog).toContainText('10,00');
  await page.getByRole('button',{name:'Ayrıntıyı kapat'}).click();
  const before=await api<{items:Stock[]}>(request,'/stocks?limit=100');
  const writes:string[]=[];page.on('request',r=>{if(r.url().includes('/api/')&&r.method()!=='GET')writes.push(r.method());});
  mkdirSync(artifact,{recursive:true});
  for(const width of [390,768,1440]) {
    await page.setViewportSize({width,height:1000});
    const row=page.locator(width<=600 ? '.data-card' : 'tbody tr').filter({hasText:code}).filter({has:page.getByRole('button',{name:'Görüntüle',exact:true})});
    const open=row.getByRole('button',{name:'Görüntüle',exact:true});await open.click();
    await expect(dialog).toBeVisible();await expect(dialog).toContainText('2,5 kg');
    await expect(dialog).toContainText('TEST tedarikçi');await expect(dialog).toContainText('TEST depo');
    expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)).toBe(false);
    await page.screenshot({path:join(artifact,`receipt-${width}.png`),fullPage:true,animations:'disabled'});
    await page.keyboard.press('Escape');await expect(dialog).not.toBeVisible();await expect(open).toBeFocused();
    if(width===1440){const a=await page.getByLabel('Miktar 1',{exact:true}).boundingBox(),b=await page.getByLabel('Toplam maliyet 1 (EUR)',{exact:true}).boundingBox();expect(Math.abs(a!.y-b!.y)).toBeLessThan(2);}
  }
  expect(writes).toEqual([]);expect(await api(request,'/stocks?limit=100')).toEqual(before);
  expect((await api<ReceiptDetail>(request,'/receipts/'+sale.id)).total_cost).toBe('10.00');
});
test('P0: gerçek kg parça ürünleri oluşturulur ve aynı reçetede farklı ürünler seçilir', async({page,request})=>{
  const code=prefix();const raw=await api<Product>(request,'/products',{sku:code,name:code+' TEST kuzu',type:'raw',base_unit:'kg'});
  await page.goto('/parcalama');await page.getByRole('button',{name:'Yeni reçete',exact:true}).click();
  await page.getByLabel('Reçete kodu',{exact:true}).fill(code);
  await page.getByLabel('Kaynak kuzu ürünü',{exact:true}).selectOption(raw.id);
  const products:Product[]=[];
  for(const [i,name] of ['But','Kol'].entries()) {
    await page.getByRole('button',{name:'Parça ürünü oluştur',exact:true}).click();
    const drawer=page.getByRole('dialog',{name:'Parça ürünü oluştur'});
    await drawer.getByLabel('SKU',{exact:true}).fill(code+'-'+i);await drawer.getByLabel('Ürün adı',{exact:true}).fill('TEST '+name);
    await expect(drawer.getByLabel('Stok birimi',{exact:true})).toHaveValue('kg');
    await drawer.getByRole('button',{name:'Parça ürününü kaydet',exact:true}).click();
    const created=page.waitForResponse(r=>r.url().endsWith('/api/v1/products')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Onayla ve kaydet',exact:true}).click();products.push(await(await created).json());
    await expect(drawer).not.toBeVisible();
    if(i)await page.getByRole('button',{name:'Reçete parçası ekle',exact:true}).click();
    await page.getByLabel('Parça ürünü '+(i+1),{exact:true}).selectOption(products[i].id);
  }
  await expect(page.getByLabel('Parça ürünü 2',{exact:true}).locator(`option[value="${products[0].id}"]`)).toBeDisabled();
  const saved=page.waitForResponse(r=>r.url().endsWith('/api/v1/recipes')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Reçeteyi kaydet',exact:true}).click();await page.getByRole('button',{name:'Onayla ve kaydet',exact:true}).click();
  expect((await(await saved).json()).lines.map((l:{product_id:string})=>l.product_id).sort()).toEqual(products.map(p=>p.id).sort());
  await expect(page.locator('.record-card').filter({hasText:code})).toBeVisible();
  mkdirSync(artifact,{recursive:true});await page.screenshot({path:join(artifact,'recipe.png'),fullPage:true,animations:'disabled'});
});
