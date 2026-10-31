import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { z } from "zod";
import { CommandForm, Field } from "../src/components/forms";
const schema = z.object({ name: z.string().min(1, "Ad gerekli.") });
function renderForm() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <CommandForm
        schema={schema}
        defaults={{ name: "" }}
        path="/products"
        label="Kaydet"
        confirmText="Ürün kaydedilecek."
        payload={(v) => v}
      >
        <Field name="name" label="Ürün adı" />
      </CommandForm>
    </QueryClientProvider>,
  );
}
afterEach(() => vi.unstubAllGlobals());
it("geçersiz formda istek göndermez; onay iptal edilebilir", async () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  renderForm();
  const user = userEvent.setup();
  expect(screen.getByLabelText("Ürün adı")).toHaveValue("");
  expect(screen.getByLabelText("Ürün adı")).toHaveAttribute("placeholder", "Örn: Dana eti");
  await user.click(screen.getByRole("button", { name: "Kaydet" }));
  expect(await screen.findByText("Ad gerekli.")).toBeVisible();
  expect(screen.getByLabelText("Ürün adı")).toHaveAttribute("aria-invalid", "true");
  expect(screen.getByLabelText("Ürün adı")).toHaveAccessibleDescription("Ad gerekli.");
  expect(fetch).not.toHaveBeenCalled();
  await user.type(screen.getByLabelText("Ürün adı"), "Et");
  await user.click(screen.getByRole("button", { name: "Kaydet" }));
  expect(await screen.findByRole("dialog")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Vazgeç" }));
  expect(fetch).not.toHaveBeenCalled();
});
it("belirsiz sonucu sekme içinde korur ve yeniden mount sonrası aynı anahtarı kullanır", async () => {
  const fetch = vi
    .fn()
    .mockRejectedValueOnce(new TypeError("offline"))
    .mockResolvedValueOnce(Response.json({ id: "ok" }));
  vi.stubGlobal("fetch", fetch);
  const rendered = renderForm(),
    user = userEvent.setup();
  await user.type(screen.getByLabelText("Ürün adı"), "Et");
  await user.click(screen.getByRole("button", { name: "Kaydet" }));
  await user.click(
    await screen.findByRole("button", { name: "Onayla ve kaydet" }),
  );
  expect(
    await screen.findByRole("button", { name: "Aynı işlemi tekrar dene" }),
  ).toBeVisible();
  expect(screen.getByLabelText("Ürün adı")).toBeDisabled();
  rendered.unmount();
  renderForm();
  expect(screen.getByLabelText("Ürün adı")).toHaveValue("Et");
  await user.click(
    screen.getByRole("button", { name: "Aynı işlemi tekrar dene" }),
  );
  await screen.findByText("Kayıt sunucu tarafından onaylandı.");
  expect(fetch.mock.calls[0][1].headers["Idempotency-Key"]).toBe(
    fetch.mock.calls[1][1].headers["Idempotency-Key"],
  );
  expect(fetch.mock.calls[0][1].body).toBe(fetch.mock.calls[1][1].body);
  await waitFor(() =>
    expect(sessionStorage.getItem("avatar.pending:/products")).toBeNull(),
  );
});

it('satır dizisinin kök doğrulama hatasını görünür gösterir',async()=>{
  const {ArrayError}=await import('../src/components/forms')
  const arraySchema=z.object({lines:z.array(z.object({name:z.string()})).superRefine((_,ctx)=>ctx.addIssue({code:'custom',message:'Aynı lot tekrarlanamaz.'}))})
  render(<QueryClientProvider client={new QueryClient()}><CommandForm schema={arraySchema} defaults={{lines:[{name:'Et'}]}} path="/receipts" label="Alışı gönder" confirmText="Alış." payload={v=>v}><Field name="lines.0.name" label="Satır adı"/><ArrayError name="lines"/></CommandForm></QueryClientProvider>)
  await userEvent.setup().click(screen.getByRole('button',{name:'Alışı gönder'}))
  expect(await screen.findByText('Aynı lot tekrarlanamaz.')).toBeVisible()
})

it("PATCH belirsiz yanıtta method/key/body korur; DELETE ve eski POST alanına taşınmaz", async () => {
  const {loadPending}=await import('../src/lib/pending');
  const path='/products/00000000-0000-4000-8000-000000000028';
  const fetch=vi.fn().mockRejectedValueOnce(new TypeError('offline')).mockResolvedValueOnce(Response.json({id:'ok'}));vi.stubGlobal('fetch',fetch);
  const mount=()=>render(<QueryClientProvider client={new QueryClient()}><CommandForm schema={schema} defaults={{name:''}} path={path} method="PATCH" label="Düzenle" confirmText="Ad güncellenecek." payload={v=>v}><Field name="name" label="Ad"/></CommandForm></QueryClientProvider>);
  const first=mount(),user=userEvent.setup();await user.type(screen.getByLabelText('Ad'),'TEST güncel');await user.click(screen.getByRole('button',{name:'Düzenle'}));await user.click(await screen.findByRole('button',{name:'Onayla ve kaydet'}));await screen.findByRole('button',{name:'Aynı işlemi tekrar dene'});
  expect(loadPending(path,'PATCH')).not.toBeNull();expect(loadPending(path,'DELETE')).toBeNull();expect(loadPending(path)).toBeNull();first.unmount();mount();
  await user.click(screen.getByRole('button',{name:'Aynı işlemi tekrar dene'}));await screen.findByText('Kayıt sunucu tarafından onaylandı.');
  expect(fetch.mock.calls[0][1].method).toBe('PATCH');expect(fetch.mock.calls[1][1]).toMatchObject({method:'PATCH',body:fetch.mock.calls[0][1].body,headers:{'Idempotency-Key':fetch.mock.calls[0][1].headers['Idempotency-Key']}});
});
