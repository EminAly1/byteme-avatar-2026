import { useFormContext } from "react-hook-form";
import { useQueryClient } from "@tanstack/react-query";
import { CommandForm, Field } from "./forms";
import { DetailDrawer } from "./dialogs";
import { productTypes, units } from "../lib/format";
import { productSchema } from "../lib/validation";
import { productPayload } from "../lib/payloads";
import type { Product } from "../lib/types";

export function ProductFields({ partOnly = false }: { partOnly?: boolean }) {
  const { watch } = useFormContext();
  return (
    <div className="form-grid">
      <Field name="sku" label="SKU" />
      <Field name="name" label="Ürün adı" />
      <Field name="type" label="Ürün türü">
        {Object.entries(productTypes).filter(([v]) => !partOnly || v !== "raw").map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </Field>
      <Field name="base_unit" label="Stok birimi">
        {Object.entries(units).filter(([v]) => !partOnly || v === "kg").map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </Field>
      {watch("base_unit") === "package" && (
        <Field
          name="package_weight_kg"
          label="Bir paket kaç kg?"
          type="decimal"
          hint="Örneğin: 1 veya 0,5"
        />
      )}
    </div>
  );
}

export function PartProductDialog({ onClose }: { onClose: () => void }) {
  const client = useQueryClient();
  return <DetailDrawer title="Parça ürünü oluştur" onClose={onClose}>
    <p className="caption">Reçete taslağınız korunur. Gerçek ürün kartı Mamul veya Yan ürün türünde, kg birimiyle kaydedilir.</p>
    <CommandForm schema={productSchema} defaults={{sku:"",name:"",type:"finished",base_unit:"kg",package_weight_kg:""}}
      path="/products" label="Parça ürününü kaydet" confirmText="Katalogda yeni kg parça ürünü oluşturulacak. Stok veya mali kayıt oluşmaz."
      payload={productPayload} onSuccess={result => {
        const product = result as Product;
        client.setQueryData<Product[]>(["records","/products"], old => [...(old || []).filter(p => p.id !== product.id), product]);
        onClose();
      }}><ProductFields partOnly /></CommandForm>
  </DetailDrawer>;
}
