"""A4 PDF in memory, embedded licensed fonts, escaped text and repeated headers."""
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from threading import Lock
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

from app.document_drafts import DISCLAIMERS

NAVY = colors.HexColor('#172b49')
GRAY = colors.HexColor('#526074')
LINE = colors.HexColor('#dbe1e9')
UNITS = {'kg': 'kg', 'package': 'paket', 'unit': 'adet'}
_font_lock = Lock()


@lru_cache(maxsize=1)
def fonts():
    with _font_lock:
        folder = Path(__file__).parent / 'assets' / 'fonts'
        for name, file in [('Document', 'DejaVuSans.ttf'), ('DocumentBold', 'DejaVuSans-Bold.ttf')]:
            pdfmetrics.registerFont(TTFont(name, str(folder / file)))
        pdfmetrics.registerFontFamily('Document', normal='Document', bold='DocumentBold')


def number(value, money=False):
    # Formatting only; totals and adjustments were read / computed by the existing ledger service.
    text = format(Decimal(value), ',.2f' if money else ',f')
    if not money and '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text.replace(',', '_').replace('.', ',').replace('_', '.') + (' EUR' if money else '')


def local_date(value):
    return datetime.fromisoformat(value).astimezone(ZoneInfo('Europe/Istanbul')).strftime('%d.%m.%Y %H:%M')


def render_pdf(data, kind, draft):
    fonts()
    output = BytesIO()
    styles = {
        'body': ParagraphStyle('body', fontName='Document', fontSize=8, leading=12, textColor=NAVY,
                               spaceAfter=3, splitLongWords=True),
        'small': ParagraphStyle('small', fontName='Document', fontSize=6.8, leading=10, textColor=GRAY,
                                spaceAfter=3, splitLongWords=True),
        'title': ParagraphStyle('title', fontName='DocumentBold', fontSize=23, leading=29,
                               textColor=NAVY, spaceAfter=10, splitLongWords=True),
        'heading': ParagraphStyle('heading', fontName='DocumentBold', fontSize=10, leading=14,
                                 textColor=NAVY, spaceBefore=9, spaceAfter=6),
        'right': ParagraphStyle('right', fontName='Document', fontSize=8, leading=12,
                               textColor=NAVY, alignment=TA_RIGHT, spaceAfter=3, splitLongWords=True),
    }

    def p(text, style='body'):
        # Paragraph supports markup; no user or database text is allowed to become markup or a URL/image.
        return Paragraph(escape(str(text or '—')).replace('\n', '<br/>').replace('\t', '    '), styles[style])

    def table(rows, widths, header=False):
        t = Table(rows, colWidths=[width * mm for width in widths], repeatRows=1 if header else 0,
                  hAlign='LEFT', splitByRow=1)
        commands = [('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5), ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('LINEBELOW', (0, 0), (-1, -1), .4, LINE)]
        if header:
            commands += [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf1f6'))]
        t.setStyle(TableStyle(commands))
        return t

    title = draft.title or ('Proforma taslağı' if kind == 'proforma' else 'Satış özeti')
    story = [p('TİCARİ BELGE / GEÇİCİ TASLAK', 'small'), p(title, 'title'), p(DISCLAIMERS[kind]),
             p('Kaynak durumu: ' + data['state_label'] + (' — GÜNCEL ÖDEME TALEBİ DEĞİLDİR' if data['state'] in ('cancelled', 'returned') else '')),
             p('KURGUSAL DEMO — kullanıcı beyanı' if draft.demo else 'Geçici taslak — sunucuda saklanmıyor', 'small'),
             p(f'Belge tarihi: {draft.document_date.strftime("%d.%m.%Y")}  ·  Taslak referansı: {draft.reference or "Girilmedi"}', 'small'),
             p('Kaynak satış: ' + data['sale_id'], 'small'),
             p('Kesin satış tarihi: ' + local_date(data['sold_at']) + ' (Türkiye saati)', 'small')]
    if draft.description:
        story += [p(draft.description)]
    story += [Spacer(1, 5 * mm), table([[
        [p('SATICI · KULLANICI TASLAĞI', 'heading'), p(draft.seller_name or 'Satıcı unvanı girilmedi'),
         p(draft.seller_contact or 'İletişim bilgisi girilmedi'), p('Doğrulanmamış, kullanıcı tarafından girilmiş bilgi.', 'small')],
        [p('MÜŞTERİ · KAYITLI İŞ ORTAĞI', 'heading'), p(data['customer']['name']),
         p(data['customer']['contact'] or 'İletişim bilgisi kayıtlı değil'),
         p('Müşteri UUID: ' + data['customer']['id'], 'small'),
         p('Güncel iş ortağı bilgisi; tarihsel fatura adresi/vergi bilgisi değildir.', 'small')],
    ]], [89, 89]), p('Kayıtlı satış kalemleri · orijinal kesin kayıt', 'heading')]
    rows = [[p('Ürün / lot'), p('Miktar / birim', 'right'), p('Birim fiyat', 'right'), p('Satır toplamı', 'right')]]
    for row in data['lines']:
        rows.append([[p(f'{row["line_no"]}. {row["product_name"]}'), p('Lot: ' + row['lot_code'], 'small'),
                      p('Lot UUID: ' + row['lot_id'], 'small')],
                     p(number(row['quantity']) + ' ' + UNITS[row['unit']], 'right'),
                     p(number(row['unit_price_eur'], True), 'right'), p(number(row['total_eur'], True), 'right')])
    story += [table(rows, [82, 27, 33, 36], header=True)]
    story += [KeepTogether([p('Kayıtlı tutarlar · EUR', 'heading'), table([
        [p('Orijinal kesin satış toplamı'), p(number(data['original_total_eur'], True), 'right')],
        [p('Kayıtlı iade gelir düzeltmesi'), p(number(data['return_credit_eur'], True), 'right')],
        [p('Kayıtlı iptal gelir düzeltmesi'), p(number(data['cancellation_credit_eur'], True), 'right')],
        [p('Düzeltme sonrası kayıtlı satış tutarı'), p(number(data['net_after_adjustments_eur'], True), 'right')],
    ], [128, 50])]), p('Durum: ' + data['state_label'], 'heading')]
    if data['state'] in ('cancelled', 'returned'):
        story += [p('GÜNCEL ÖDEME TALEBİ DEĞİLDİR. İptal/tam iade orijinal kaydı silmez.')]
    elif data['state'] == 'partially_returned':
        story += [p('KISMİ İADE: Orijinal satış ve sonraki gelir düzeltmeleri ayrı gösterilmiştir.')]
    story += [p('Tahsilat ve nakit iade durumu kayıtlı değil; ödendi veya ödenecek bakiye beyan edilmez.', 'small'),
              p('Vergi/KDV bilgisi kayıtlı değil; oran veya dahil/hariç tutar hesaplanmadı.', 'small')]
    for correction in data['corrections']:
        label = 'Müşteri iadesi' if correction['kind'] == 'return' else 'Satış iptali'
        story += [p(label + ' · ' + correction['id'], 'heading'),
                  p(local_date(correction['recorded_at']) + ' · ' + correction['reason']),
                  p('Kayıtlı gelir düzeltmesi: ' + number(correction['credit_eur'], True))]
        for row in correction['lines']:
            original = next(line for line in data['lines'] if line['id'] == row['sale_line_id'])
            story += [p(f'{original["product_name"]} · {original["lot_code"]}: {number(row["quantity"])} {UNITS[row["unit"]]} · {number(row["credit_eur"], True)}', 'small')]
    story += [p('Satışa gerçekten bağlı sevkiyatlar', 'heading')]
    if not data['shipments']:
        story += [p('Bu satışa bağlı sevkiyat kaydı yok. Bağımsız sevkiyattan fiyat türetilmez.')]
    for shipment in data['shipments']:
        story += [p(shipment['id'], 'small'), p(local_date(shipment['shipped_at']) + ' · ' + shipment['recipient_name'])]
        for line in shipment['lines']:
            original = next(row for row in data['lines'] if row['id'] == line['sale_line_id'])
            story += [p(original['lot_code'] + ' · ' + number(line['quantity']) + ' ' + UNITS[line['unit']], 'small')]
    for label, value in [('Ödeme / vade açıklaması', draft.payment_note), ('Teslimat açıklaması', draft.delivery_note), ('Özel not', draft.note)]:
        if value:
            story += [p(label, 'heading'), p(value)]
    story += [Spacer(1, 6 * mm), p('Bu belge GİB e-Fatura/e-Arşiv belgesi değildir. Resmî fatura numarası, vergi hesabı veya mali gönderim içermez. Taslak düzenlemeleri kesin satış, stok, lot ve maliyet kayıtlarını değiştirmez.', 'small')]

    def chrome(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(1.4)
        canvas.line(16 * mm, 286 * mm, 194 * mm, 286 * mm)
        # Neutral geometry, not a new product logo or brand.
        canvas.setFillColor(NAVY)
        canvas.rect(16 * mm, 287 * mm, 3 * mm, 3 * mm, fill=1, stroke=0)
        canvas.setFont('Document', 6.2)
        canvas.drawString(16 * mm, 12 * mm, DISCLAIMERS[kind])
        canvas.drawRightString(194 * mm, 12 * mm, f'Sayfa {doc.page}')
        canvas.drawString(16 * mm, 8 * mm, 'Durum: ' + data['state_label'] + ' · ' + ('KURGUSAL DEMO' if draft.demo else 'GEÇİCİ TASLAK'))
        canvas.restoreState()

    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm,
                            topMargin=17 * mm, bottomMargin=20 * mm,
                            title=DISCLAIMERS[kind], author='Document draft', pageCompression=1)
    doc.build(story, onFirstPage=chrome, onLaterPages=chrome)
    return output.getvalue()
