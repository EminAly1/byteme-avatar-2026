import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { DetailDrawer } from "./dialogs";
import { CommandForm, Field } from "./forms";
import { State } from "./ui";
import { RecordId } from "./presentation";
import { request } from "../lib/api";
import { amount, dateTime, locationKinds, productTypes, roles, units } from "../lib/format";
export type MasterKind = "products" | "parties" | "locations";
export type MasterSelection = { id: string; mode: "view" | "edit" | "delete" };
const names = { products: "Ürün", parties: "Firma", locations: "Depo" };
const nameSchema = z.object({ name: z.string().trim().min(1,"Ad gerekli.").max(200,"En fazla 200 karakter.") });
const partySchema = nameSchema.extend({ contact: z.string().trim().max(300,"En fazla 300 karakter.") });
const labels: Record<string,string> = {name:"Ad",sku:"Ürün kodu (SKU)",type:"Ürün türü",base_unit:"Stok birimi",package_weight_kg:"Paket ağırlığı (kg)",species:"Hayvan türü",roles:"Firma rolleri",contact:"İletişim",kind:"Konum türü",created_at:"Oluşturulma tarihi"};
function value(key:string,v:unknown):string {
  if(v==null || v==="")return "Belirtilmedi";
  if(key==="roles")return (v as string[]).map(r=>roles[r as keyof typeof roles] || r).join(", ");
  if(key==="type")return productTypes[v as keyof typeof productTypes] || String(v);
  if(key==="base_unit")return units[v as keyof typeof units] || String(v);
  if(key==="kind")return locationKinds[v as keyof typeof locationKinds] || String(v);
  if(key==="package_weight_kg")return amount(String(v));
  if(key==="created_at")return dateTime(String(v));
  return String(v);
}
export function MasterRecordDialog({ kind, selection, onClose }: {kind:MasterKind;selection:MasterSelection;onClose:()=>void}) {
  const path="/"+kind+"/"+selection.id;
  const q=useQuery({queryKey:["master-detail",kind,selection.id],queryFn:()=>request<Record<string,unknown>>(path),retry:false});
  return <DetailDrawer title={names[kind]+(selection.mode==="view"?" ayrıntıları":selection.mode==="edit"?" düzenle":" silme kontrolü")} onClose={onClose}>
    <State loading={q.isPending} error={q.error}>{q.data && <>
      <dl className="record-facts">{Object.entries(q.data).filter(([key])=>key in labels).map(([key,v])=><div key={key}><dt>{labels[key]}</dt><dd>{value(key,v)}</dd></div>)}</dl>
      <RecordId id={String(q.data.id)} label="Kayıt kimliği"/>
      {q.data.party_id!=null && <RecordId id={String(q.data.party_id)} label="Bağlı firma kimliği"/>}
      {selection.mode==="edit" && <>
        <p className="caption">Yalnız ad{kind==="parties"?" ve iletişim":""} düzenlenir. Kimlik, tür, birim, dönüşüm, roller ve konum ilişkileri geçmişi korumak için kilitlidir.</p>
        {kind==="parties" ? <CommandForm key={path} schema={partySchema} defaults={{name:String(q.data.name),contact:String(q.data.contact||"")}} path={path} method="PATCH" label="Değişikliği gözden geçir" confirmText="Yalnız firmanın adı ve iletişim bilgisi güncellenecek. Geçmiş işlemler ve roller korunur." payload={v=>({...v,contact:v.contact||null})} onSuccess={onClose}><div className="form-grid"><Field name="name" label="Ad"/><Field name="contact" label="İletişim bilgisi"/></div></CommandForm>
        : <CommandForm key={path} schema={nameSchema} defaults={{name:String(q.data.name)}} path={path} method="PATCH" label="Değişikliği gözden geçir" confirmText="Yalnız kartın adı güncellenecek; kesin kayıtlar değişmeyecek." payload={v=>v} onSuccess={onClose}><Field name="name" label="Ad"/></CommandForm>}
      </>}
      {selection.mode==="delete" && <CommandForm schema={z.object({})} defaults={{}} path={path} method="DELETE" danger label="Silmeyi gözden geçir" confirmText="Bu ana kart kalıcı silinecek. Sunucu bağlı iş kaydı varsa işlemi reddeder; kesin geçmiş silinmez." payload={()=>({})} onSuccess={onClose}><p><strong>{String(q.data.name)}</strong> yalnız başka kart veya iş kaydına bağlı değilse silinebilir. Arşivleme veya geçmiş silme yapılmaz.</p></CommandForm>}
    </>}</State>
  </DetailDrawer>;
}
