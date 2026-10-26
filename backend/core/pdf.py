"""Génération des documents PDF (facture, reçu, ticket, bon de livraison)."""
from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.models import ShopSetting


def fcfa(amount):
    return f"{int(amount or 0):,} FCFA".replace(",", " ")


def _header_footer(canvas, doc, title, shop):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(colors.HexColor("#111827"))
    canvas.rect(0, height - 28 * mm, width, 28 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#f5b301"))
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawString(18 * mm, height - 15 * mm, shop.shop_name)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(18 * mm, height - 21 * mm, f"{shop.address} — WhatsApp {shop.whatsapp_phone}")
    canvas.drawRightString(width - 18 * mm, height - 15 * mm, title)
    canvas.drawRightString(
        width - 18 * mm, height - 21 * mm, timezone.localtime().strftime("%d/%m/%Y %H:%M")
    )
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(
        18 * mm,
        12 * mm,
        f"{shop.shop_name} — {shop.phone or shop.whatsapp_phone} — Orange Money {shop.orange_money_phone}",
    )
    canvas.restoreState()


def _doc(buffer, title, shop):
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=34 * mm,
        bottomMargin=22 * mm,
        title=title,
        author=shop.shop_name,
    )
    return doc


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="KssBody", parent=styles["Normal"], fontSize=9, leading=13,
            textColor=colors.HexColor("#111827"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="KssTitle", parent=styles["Title"], fontSize=16, spaceAfter=6,
            textColor=colors.HexColor("#111827"),
        )
    )
    return styles


def invoice_pdf(order, kind="invoice"):
    """Document de vente : facture, reçu, ticket 80 mm ou bon de livraison."""
    shop = ShopSetting.load()
    titles = {
        "invoice": "FACTURE",
        "receipt": "REÇU DE VENTE",
        "ticket": "TICKET DE CAISSE",
        "delivery": "BON DE LIVRAISON",
    }
    title = titles.get(kind, "FACTURE")

    if kind == "ticket":
        return _ticket_pdf(order, shop)
    if kind == "receipt":
        return _receipt_pdf(order, shop)

    buffer = BytesIO()
    doc = _doc(buffer, f"{title} {order.number}", shop)
    styles = _styles()
    story = [Paragraph(f"{title} N° {order.number}", styles["KssTitle"])]
    story.append(Paragraph(f"Date : {timezone.localtime(order.created_at):%d/%m/%Y %H:%M}", styles["KssBody"]))
    customer = order.user.full_name if order.user else order.customer_name
    phone = order.user.phone if order.user else order.customer_phone
    story.append(Paragraph(f"Client : {customer or 'Comptoir'} — {phone or ''}", styles["KssBody"]))
    if order.delivery_address_text:
        story.append(Paragraph(f"Livraison : {order.delivery_address_text}", styles["KssBody"]))
    story.append(Spacer(1, 6))

    rows = [["Désignation", "Qté", "Prix unitaire", "Total"]]
    for item in order.items.all():
        rows.append(
            [item.product_name + (f" ({item.variant_label})" if item.variant_label else ""),
             str(item.quantity), fcfa(item.unit_price_sale), fcfa(item.line_total_sale)]
        )
    rows.append(["", "", "Sous-total", fcfa(order.subtotal)])
    if order.discount:
        rows.append(["", "", "Remise", f"-{fcfa(order.discount)}"])
    rows.append(["", "", "Livraison", "Gratuite"])
    rows.append(["", "", "TOTAL", fcfa(order.total)])
    rows.append(["", "", "Payé", fcfa(order.amount_paid)])
    rows.append(["", "", "Solde dû", fcfa(order.balance_due)])

    table = Table(rows, colWidths=[82 * mm, 14 * mm, 38 * mm, 38 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -5), "Helvetica"),
                ("FONTNAME", (0, -3), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -5), [colors.white, colors.HexColor("#f9fafb")]),
                ("BACKGROUND", (0, -3), (-1, -1), colors.HexColor("#fef3c7")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            f"Statut : {order.get_status_display()} — Paiement : {order.payment_status_display}",
            styles["KssBody"],
        )
    )
    story.append(
        Paragraph(
            "Paiement accepté : espèces, Orange Money (référence de transaction). "
            "La commande est préparée après vérification du paiement.",
            styles["KssBody"],
        )
    )
    if kind == "delivery":
        story.append(Spacer(1, 26))
        story.append(Paragraph("Signature du client : ______________________", styles["KssBody"]))
        story.append(Paragraph("Nom du livreur : __________________________", styles["KssBody"]))
        story.append(Paragraph("Date et heure de remise : ________________", styles["KssBody"]))

    doc.build(story, onFirstPage=lambda c, d: _header_footer(c, d, title, shop),
              onLaterPages=lambda c, d: _header_footer(c, d, title, shop))
    buffer.seek(0)
    return buffer


def _receipt_pdf(order, shop):
    """Reçu de vente : justificatif des encaissements, partageable au client."""
    payments = list(order.payments.all().order_by("created_at"))

    buffer = BytesIO()
    doc = _doc(buffer, f"Reçu {order.number}", shop)
    styles = _styles()
    story = [Paragraph(f"REÇU DE VENTE N° {order.number}", styles["KssTitle"])]
    story.append(
        Paragraph(
            f"Émis le {timezone.localtime():%d/%m/%Y à %H:%M}",
            styles["KssBody"],
        )
    )
    customer = order.user.full_name if order.user else order.customer_name
    phone = order.user.phone if order.user else order.customer_phone
    story.append(Paragraph(f"Client : {customer or 'Comptoir'} — {phone or ''}", styles["KssBody"]))
    story.append(Spacer(1, 8))

    rows = [["Date", "Moyen de paiement", "Référence", "Montant"]]
    for payment in payments:
        rows.append(
            [
                timezone.localtime(payment.created_at).strftime("%d/%m/%Y %H:%M"),
                payment.get_method_display(),
                payment.om_reference or payment.get_status_display(),
                fcfa(payment.amount),
            ]
        )
    payments_table = Table(rows, colWidths=[38 * mm, 46 * mm, 56 * mm, 32 * mm], repeatRows=1)
    payments_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(payments_table)
    story.append(Spacer(1, 10))

    totals = Table(
        [
            ["Total de la commande", fcfa(order.total)],
            ["Total encaissé", fcfa(order.amount_paid)],
            ["Reste à payer", fcfa(order.balance_due)],
        ],
        colWidths=[60 * mm, 112 * mm],
    )
    totals.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#fef3c7")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(totals)
    story.append(Spacer(1, 10))

    if order.balance_due > 0:
        story.append(
            Paragraph(
                f"Acompte reçu. Le solde de {fcfa(order.balance_due)} reste à régler à la remise.",
                styles["KssBody"],
            )
        )
    else:
        story.append(
            Paragraph("Vente intégralement réglée. Merci de votre confiance.", styles["KssBody"])
        )
    if shop.return_delay_days:
        story.append(
            Paragraph(
                f"Échange possible sous {shop.return_delay_days} jours sur présentation de ce reçu.",
                styles["KssBody"],
            )
        )

    doc.build(
        story,
        onFirstPage=lambda c, d: _header_footer(c, d, "REÇU DE VENTE", shop),
        onLaterPages=lambda c, d: _header_footer(c, d, "REÇU DE VENTE", shop),
    )
    buffer.seek(0)
    return buffer


def _ticket_pdf(order, shop):
    """Ticket de caisse 80 mm."""
    from reportlab.lib.pagesizes import mm as _mm  # noqa: F401

    width = 80 * mm
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=(width, 260 * mm), leftMargin=5 * mm, rightMargin=5 * mm,
        topMargin=6 * mm, bottomMargin=6 * mm, title=f"Ticket {order.number}",
    )
    styles = _styles()
    story = [
        Paragraph(f"<b>{shop.shop_name}</b>", styles["KssBody"]),
        Paragraph(f"{shop.address}<br/>{shop.phone or shop.whatsapp_phone}", styles["KssBody"]),
        Spacer(1, 4),
        Paragraph(f"<b>Ticket {order.number}</b>", styles["KssBody"]),
        Paragraph(timezone.localtime(order.created_at).strftime("%d/%m/%Y %H:%M"), styles["KssBody"]),
        Spacer(1, 4),
    ]
    for item in order.items.all():
        story.append(
            Paragraph(
                f"{item.product_name} x{item.quantity}<br/>{fcfa(item.line_total_sale)}",
                styles["KssBody"],
            )
        )
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Sous-total : {fcfa(order.subtotal)}", styles["KssBody"]))
    if order.discount:
        story.append(Paragraph(f"Remise : -{fcfa(order.discount)}", styles["KssBody"]))
    story.append(Paragraph(f"<b>TOTAL : {fcfa(order.total)}</b>", styles["KssBody"]))
    story.append(Paragraph(f"Payé : {fcfa(order.amount_paid)} / Solde : {fcfa(order.balance)}", styles["KssBody"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Merci de votre confiance !", styles["KssBody"]))
    doc.build(story)
    buffer.seek(0)
    return buffer
