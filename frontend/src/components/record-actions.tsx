import type { ReactNode } from "react";
export function RecordActions({ onView, onEdit, onDelete, children, readonlyReason = "Kesin kayıt korunur; düzenleme ve silme desteklenmez." }: {
  onView?: () => void; onEdit?: () => void; onDelete?: () => void; children?: ReactNode; readonlyReason?: string;
}) {
  return <div className="record-actions">
    {onView && <button type="button" className="text-button" onClick={onView}>Görüntüle</button>}
    {children}
    <button type="button" className="text-button" disabled={!onEdit} title={!onEdit ? readonlyReason : undefined} onClick={onEdit}>Düzenle</button>
    <button type="button" className="text-button danger-text" disabled={!onDelete} title={!onDelete ? readonlyReason : undefined} onClick={onDelete}>Sil</button>
    {!onEdit && !onDelete && <small className="caption">{readonlyReason}</small>}
  </div>;
}

import { useState } from "react";
import { DetailDrawer } from "./dialogs";
export function ReadOnlyRowActions({ facts, children, reason }: { facts: Array<[string,ReactNode]>; children?:ReactNode; reason:string }) {
  const [open,setOpen]=useState(false);
  return <><RecordActions onView={children ? undefined : ()=>setOpen(true)} readonlyReason={reason}>{children}</RecordActions>
    {open && <DetailDrawer title="Kayıt özeti" onClose={()=>setOpen(false)}>
      <p className="caption">Listede alınan gerçek sunucu özeti. Varsa işlem bağlantısı tam kaydı açar.</p>
      <dl className="record-facts">{facts.map(([label,value],i)=><div key={i}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
      <p className="caption">{reason}</p>
    </DetailDrawer>}
  </>;
}
