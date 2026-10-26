import csv
import datetime as dt
from collections import Counter

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Product, ProductVariant
from core.permissions import IsOwner
from deliveries.models import Delivery
from orders.models import Order, OrderItem
from payments.models import Payment

REVENUE_STATUSES = [
    Order.Status.CONFIRMED,
    Order.Status.PREPARING,
    Order.Status.SHIPPING,
    Order.Status.DELIVERED,
]
REVENUE_FILTER = Q(status__in=REVENUE_STATUSES)

def date_range(request, default_days=30):
    today = timezone.localdate()
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")
    try:
        start = dt.date.fromisoformat(date_from) if date_from else today - dt.timedelta(days=default_days - 1)
        end = dt.date.fromisoformat(date_to) if date_to else today
    except ValueError:
        start, end = today - dt.timedelta(days=default_days - 1), today
    return start, end

def orders_between(start, end, statuses=None):
    qs = Order.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
    if statuses:
        qs = qs.filter(status__in=statuses)
    return qs


class DashboardView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        today = timezone.localdate()
        now = timezone.now()
        orders_today = orders_between(today, today)
        revenue_today = orders_today.filter(REVENUE_FILTER).aggregate(total=Sum("total"))["total"] or 0

        payments_pending = Payment.objects.filter(status=Payment.Status.PENDING)
        pending_orders = Order.objects.filter(status=Order.Status.PENDING_PAYMENT)
        stale = pending_orders.filter(created_at__lt=now - dt.timedelta(hours=24))
        low_stock = ProductVariant.objects.filter(
            is_active=True, stock_qty__lte=F("low_stock_threshold")
        ).select_related("product")

        deliveries_today = Delivery.objects.filter(
            Q(order__desired_date=today) | Q(created_at__date=today)
        ).exclude(status=Delivery.Status.DELIVERED)
        overdue = Delivery.objects.filter(
            status__in=[Delivery.Status.TO_PREPARE, Delivery.Status.IN_TRANSIT],
            order__desired_date__lt=today,
        )

        def series(days):
            start = today - dt.timedelta(days=days - 1)
            rows = (
                orders_between(start, today, REVENUE_STATUSES)
                .annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(total=Sum("total"), orders=Count("id"))
                .order_by("day")
            )
            data = {row["day"].isoformat(): row for row in rows}
            result = []
            for i in range(days):
                day = start + dt.timedelta(days=i)
                row = data.get(day.isoformat())
                result.append(
                    {
                        "date": day.isoformat(),
                        "total": row["total"] if row else 0,
                        "orders": row["orders"] if row else 0,
                    }
                )
            return result

        category_rows = (
            OrderItem.objects.filter(order__in=orders_between(today - dt.timedelta(days=29), today, REVENUE_STATUSES))
            .values("variant__product__category__name")
            .annotate(total=Sum("line_total_sale"), quantity=Sum("quantity"))
            .order_by("-total")
        )
        categories = [
            {
                "name": row["variant__product__category__name"] or "Sans catégorie",
                "total": row["total"] or 0,
                "quantity": row["quantity"] or 0,
            }
            for row in category_rows
        ]

        return Response(
            {
                "today": {
                    "revenue": revenue_today,
                    "orders": orders_today.count(),
                    "orders_to_process": orders_today.filter(
                        status__in=[Order.Status.PENDING_PAYMENT, Order.Status.CONFIRMED, Order.Status.PREPARING]
                    ).count(),
                    "payments_to_verify": payments_pending.count(),
                    "payments_to_verify_amount": payments_pending.aggregate(total=Sum("amount"))["total"] or 0,
                    "deliveries": deliveries_today.count(),
                },
                "sales_7_days": series(7),
                "sales_30_days": series(30),
                "categories": categories,
                "alerts": {
                    "low_stock": [
                        {
                            "variant": v.id,
                            "product": v.product.name,
                            "label": v.label,
                            "stock_qty": v.stock_qty,
                            "threshold": v.low_stock_threshold,
                        }
                        for v in low_stock[:20]
                    ],
                    "low_stock_count": low_stock.count(),
                    "stale_unpaid": stale.count(),
                    "stale_unpaid_amount": stale.aggregate(total=Sum("total"))["total"] or 0,
                    "overdue_deliveries": overdue.count(),
                    "outstanding_balance": Order.objects.filter(REVENUE_FILTER).aggregate(
                        total=Sum("balance_due")
                    )["total"] or 0,
                },
            }
        )


class ReportsView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        start, end = date_range(request)
        orders = orders_between(start, end, REVENUE_STATUSES)
        all_orders = orders_between(start, end)

        revenue = orders.aggregate(total=Sum("total"))["total"] or 0
        subtotal = orders.aggregate(total=Sum("subtotal"))["total"] or 0
        discounts = orders.aggregate(total=Sum("discount"))["total"] or 0
        collected = orders.aggregate(total=Sum("amount_paid"))["total"] or 0
        outstanding = orders.aggregate(total=Sum("balance_due"))["total"] or 0

        items = OrderItem.objects.filter(order__in=orders)
        purchase_cost = items.aggregate(total=Sum("line_total_purchase"))["total"] or 0
        gross_margin = (items.aggregate(total=Sum("line_total_sale"))["total"] or 0) - purchase_cost
        delivery_cost = Delivery.objects.filter(order__in=orders).aggregate(
            total=Sum("delivery_cost")
        )["total"] or 0

        top_products = list(
            items.values("product_name")
            .annotate(
                quantity=Sum("quantity"),
                revenue=Sum("line_total_sale"),
                margin=Sum(F("line_total_sale") - F("line_total_purchase")),
            )
            .order_by("-revenue")[:5]
        )
        top_categories = list(
            items.values("variant__product__category__name")
            .annotate(revenue=Sum("line_total_sale"), quantity=Sum("quantity"))
            .order_by("-revenue")[:5]
        )
        payments_by_method = list(
            Payment.objects.filter(
                status=Payment.Status.CONFIRMED, created_at__date__gte=start, created_at__date__lte=end
            )
            .values("method")
            .annotate(total=Sum("amount"), count=Count("id"))
        )
        channels = list(
            all_orders.values("channel").annotate(total=Sum("total"), count=Count("id"))
        )
        sales_series = list(
            orders.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("total"), orders=Count("id"))
            .order_by("day")
        )

        stock_variants = ProductVariant.objects.filter(is_active=True)
        stock_value = sum(v.stock_qty * v.price_purchase for v in stock_variants)
        low_stock_count = stock_variants.filter(stock_qty__lte=F("low_stock_threshold")).count()

        deliveries = Delivery.objects.filter(order__in=all_orders)
        deliveries_by_status = list(
            deliveries.values("status").annotate(count=Count("id"))
        )
        deliveries_by_courier = list(
            deliveries.exclude(courier_name="")
            .values("courier_name")
            .annotate(count=Count("id"), cost=Sum("delivery_cost"))
        )
        deliveries_by_zone = list(
            deliveries.exclude(order__delivery_district="")
            .values("order__delivery_district")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        return Response(
            {
                "period": {"date_from": start.isoformat(), "date_to": end.isoformat()},
                "totals": {
                    "revenue": revenue,
                    "orders": all_orders.count(),
                    "valid_orders": orders.count(),
                    "subtotal": subtotal,
                    "discounts": discounts,
                    "collected": collected,
                    "outstanding": outstanding,
                    "purchase_cost": purchase_cost,
                    "gross_margin": gross_margin,
                    "delivery_cost": delivery_cost,
                    "net_margin": gross_margin - delivery_cost,
                },
                "sales_series": [
                    {"date": row["day"].isoformat(), "total": row["total"], "orders": row["orders"]}
                    for row in sales_series
                ],
                "top_products": [
                    {
                        "name": row["product_name"],
                        "quantity": row["quantity"],
                        "revenue": row["revenue"],
                        "margin": row["margin"],
                    }
                    for row in top_products
                ],
                "top_categories": [
                    {
                        "name": row["variant__product__category__name"],
                        "revenue": row["revenue"],
                        "quantity": row["quantity"],
                    }
                    for row in top_categories
                ],
                "payments_by_method": [
                    {"method": row["method"], "total": row["total"], "count": row["count"]}
                    for row in payments_by_method
                ],
                "channels": channels,
                "stock": {
                    "value_purchase": stock_value,
                    "low_stock_count": low_stock_count,
                    "products_count": Product.objects.filter(status="published").count(),
                },
                "deliveries": {
                    "by_status": deliveries_by_status,
                    "by_courier": deliveries_by_courier,
                    "by_zone": deliveries_by_zone,
                },
            }
        )


class ExportCSVView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        export_type = request.query_params.get("type", "sales")
        start, end = date_range(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response.write("\ufeff")

        if export_type == "stock":
            response["Content-Disposition"] = 'attachment; filename="stock.csv"'
            writer = csv.writer(response, delimiter=";")
            writer.writerow(
                ["Produit", "Variante", "SKU", "Stock", "Seuil", "Prix achat", "Prix vente", "Valeur achat"]
            )
            for v in ProductVariant.objects.filter(is_active=True).select_related("product"):
                writer.writerow(
                    [v.product.name, v.label, v.sku, v.stock_qty, v.low_stock_threshold,
                     v.price_purchase, v.price_sale, v.stock_qty * v.price_purchase]
                )
            return response

        if export_type == "payments":
            response["Content-Disposition"] = 'attachment; filename="paiements.csv"'
            writer = csv.writer(response, delimiter=";")
            writer.writerow(["Date", "Commande", "Client", "Moyen", "Montant", "Réf. Orange Money", "Statut"])
            for p in Payment.objects.filter(
                created_at__date__gte=start, created_at__date__lte=end
            ).select_related("order"):
                writer.writerow(
                    [p.created_at.strftime("%d/%m/%Y %H:%M"), p.order.number, p.order.customer_name,
                     p.get_method_display(), p.amount, p.om_reference or "", p.get_status_display()]
                )
            return response

        if export_type == "products":
            response["Content-Disposition"] = 'attachment; filename="ventes-produits.csv"'
            writer = csv.writer(response, delimiter=";")
            writer.writerow(["Produit", "Quantité vendue", "Chiffre d'affaires", "Marge brute"])
            rows = (
                OrderItem.objects.filter(order__in=orders_between(start, end, REVENUE_STATUSES))
                .values("product_name")
                .annotate(
                    quantity=Sum("quantity"),
                    revenue=Sum("line_total_sale"),
                    margin=Sum(F("line_total_sale") - F("line_total_purchase")),
                )
                .order_by("-revenue")
            )
            for row in rows:
                writer.writerow([row["product_name"], row["quantity"], row["revenue"], row["margin"]])
            return response

        response["Content-Disposition"] = 'attachment; filename="ventes.csv"'
        writer = csv.writer(response, delimiter=";")
        writer.writerow(
            ["Numéro", "Date", "Client", "Téléphone", "Canal", "Statut", "Sous-total",
             "Remise", "Total", "Payé", "Solde", "Moyen de paiement"]
        )
        for order in orders_between(start, end).prefetch_related("payments"):
            methods = ", ".join(sorted({p.get_method_display() for p in order.payments.all()}))
            writer.writerow(
                [order.number, order.created_at.strftime("%d/%m/%Y %H:%M"), order.customer_name,
                 order.customer_phone, order.get_channel_display(), order.get_status_display(),
                 order.subtotal, order.discount, order.total, order.amount_paid, order.balance_due, methods]
            )
        return response


class ExportPDFView(APIView):
    """Export PDF avancé avec filtres admin.
    
    Types supportés :
    - 'orders' : Liste des commandes avec détails
    - 'payments' : Encaissements récapitulatif
    - 'deliveries' : Liste des livraisons
    - 'products' : Catalogue produits avec stock
    - 'summary' : Rapport financier récapitulatif
    """
    permission_classes = [IsOwner]

    def get(self, request):
        export_type = request.query_params.get("type", "summary")
        start, end = date_range(request)

        if export_type == "orders":
            return self._export_orders_pdf(request, start, end)
        elif export_type == "payments":
            return self._export_payments_pdf(request, start, end)
        elif export_type == "deliveries":
            return self._export_deliveries_pdf(request, start, end)
        elif export_type == "products":
            return self._export_products_pdf(request, start, end)
        else:
            return self._export_summary_pdf(request, start, end)

    def _export_summary_pdf(self, request, start, end):
        """Export PDF du rapport financier récapitulatif."""
        from io import BytesIO
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        from catalog.models import Product, ProductVariant
        from core.models import ShopSetting
        from deliveries.models import Delivery
        from orders.models import Order, OrderItem
        from payments.models import Payment

        shop = ShopSetting.load()

        revenue = Order.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end,
            status__in=[Order.Status.CONFIRMED, Order.Status.PREPARING, Order.Status.SHIPPING, Order.Status.DELIVERED]
        ).aggregate(total=Sum("total"))["total"] or 0

        subtotal = Order.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end
        ).aggregate(total=Sum("subtotal"))["total"] or 0

        discounts = Order.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end
        ).aggregate(total=Sum("discount"))["total"] or 0

        collected = Order.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end
        ).aggregate(total=Sum("amount_paid"))["total"] or 0

        outstanding = Order.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end
        ).aggregate(total=Sum("balance_due"))["total"] or 0

        items = OrderItem.objects.filter(
            order__in=Order.objects.filter(
                created_at__date__gte=start, created_at__date__lte=end,
                status__in=[Order.Status.CONFIRMED, Order.Status.PREPARING, Order.Status.SHIPPING, Order.Status.DELIVERED]
            )
        )
        purchase_cost = items.aggregate(total=Sum("line_total_purchase"))["total"] or 0
        gross_margin = (items.aggregate(total=Sum("line_total_sale"))["total"] or 0) - purchase_cost

        # Calculs de marge
        delivery_cost = Delivery.objects.filter(
            order__in=Order.objects.filter(
                created_at__date__gte=start, created_at__date__lte=end,
                status__in=[Order.Status.CONFIRMED, Order.Status.PREPARING, Order.Status.SHIPPING, Order.Status.DELIVERED]
            )
        ).aggregate(total=Sum("delivery_cost"))["total"] or 0

        net_margin = gross_margin - delivery_cost

        # Top produits
        top_products = list(
            items.values("product_name")
            .annotate(quantity=Sum("quantity"), revenue=Sum("line_total_sale"), margin=Sum(F("line_total_sale") - F("line_total_purchase")))
            .order_by("-revenue")[:10]
        )

        # Top catégories
        top_categories = list(
            items.values("variant__product__category__name")
            .annotate(revenue=Sum("line_total_sale"), quantity=Sum("quantity"))
            .order_by("-revenue")[:5]
        )

        # Paiements par méthode
        payments_by_method = list(
            Payment.objects.filter(
                status=Payment.Status.CONFIRMED, created_at__date__gte=start, created_at__date__lte=end
            ).values("method").annotate(total=Sum("amount"), count=Count("id"))
        )

        # Séries temporelles
        sales_series = list(
            Order.objects.filter(
                created_at__date__gte=start, created_at__date__lte=end,
                status__in=[Order.Status.CONFIRMED, Order.Status.PREPARING, Order.Status.SHIPPING, Order.Status.DELIVERED]
            ).annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("total"), orders=Count("id"))
            .order_by("day")
        )

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=25 * mm, bottomMargin=25 * mm,
        )
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="KssTitle", parent=styles["Title"], fontSize=18, spaceAfter=6, textColor=colors.HexColor("#111827")))
        styles.add(ParagraphStyle(name="KssBody", parent=styles["Normal"], fontSize=10, leading=13, textColor=colors.HexColor("#111827")))
        styles.add(ParagraphStyle(name="KssSub", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#6b7280")))

        story = []

        # En-tête
        story.append(Paragraph(f"RAPPORT FINANCIER — Konaté-Service-Gym", styles["KssTitle"]))
        story.append(Paragraph(f"Période : {start.strftime('%d/%m/%Y')} au {end.strftime('%d/%m/%Y')}", styles["KssBody"]))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"Généré le {timezone.localtime().strftime('%d/%m/%Y %H:%M')}", styles["KssBody"]))
        story.append(Spacer(1, 8))

        # En-tête du tableau principal
        story.append(Paragraph("RÉSUMÉ FINANCIER", styles["KssSub"]))
        story.append(Spacer(1, 4))

        # Tableau des KPIs
        kpi_data = [
            ["Chiffre d'affaires", fcfa(revenue)],
            ["Sous-total", fcfa(subtotal)],
            ["Remises", f"-{fcfa(discounts)}"],
            ["Total encaissé", fcfa(collected)],
            ["Solde dû", fcfa(outstanding)],
            ["Marge brute", fcfa(gross_margin)],
            ["Coût livraison", fcfa(delivery_cost)],
            ["Marge nette", fcfa(net_margin)],
        ]

        kpi_table = Table(kpi_data, colWidths=[6 * inch, 2 * inch])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 12))

        # Top produits
        story.append(Paragraph("TOP 10 PRODUITS", styles["KssSub"]))
        story.append(Spacer(1, 4))

        if top_products:
            prod_data = [["Produit", "Quantité", "Chiffre d'affaires", "Marge"]]
            for p in top_products:
                prod_data.append([
                    p["product_name"][:30] if len(p["product_name"]) > 30 else p["product_name"],
                    str(p["quantity"] or 0),
                    fcfa(p["revenue"] or 0),
                    fcfa(p["margin"] or 0),
                ])
            prod_table = Table(prod_data, colWidths=[3.5 * inch, 1 * inch, 1.7 * inch, 1.7 * inch])
            prod_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ]))
            story.append(prod_table)
        else:
            story.append(Paragraph("Aucune donnée disponible", styles["KssBody"]))
        story.append(Spacer(1, 8))

        # Top catégories
        story.append(Paragraph("TOP 5 CATÉGORIES", styles["KssSub"]))
        story.append(Spacer(1, 4))

        if top_categories:
            cat_data = [["Catégorie", "Chiffre d'affaires", "Quantité"]]
            for c in top_categories:
                cat_data.append([
                    c["variant__product__category__name"] or "Sans catégorie",
                    fcfa(c["revenue"] or 0),
                    str(c["quantity"] or 0),
                ])
            cat_table = Table(cat_data, colWidths=[3 * inch, 2 * inch, 1.5 * inch])
            cat_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ]))
            story.append(cat_table)
        else:
            story.append(Paragraph("Aucune donnée disponible", styles["KssBody"]))
        story.append(Spacer(1, 8))

        # Paiements par méthode
        story.append(Paragraph("RÉPARTITION DES PAIEMENTS", styles["KssSub"]))
        story.append(Spacer(1, 4))

        if payments_by_method:
            pay_data = [["Moyen de paiement", "Montant total", "Nombre de transactions"]]
            for p in payments_by_method:
                pay_data.append([
                    p["method"] or "Non spécifié",
                    fcfa(p["total"] or 0),
                    str(p["count"] or 0),
                ])
            pay_table = Table(pay_data, colWidths=[2.5 * inch, 2 * inch, 2 * inch])
            pay_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ]))
            story.append(pay_table)
        else:
            story.append(Paragraph("Aucune donnée disponible", styles["KssBody"]))
        story.append(Spacer(1, 8))

        # Séries temporelles
        story.append(Paragraph("ÉVOLUTION JOURNALIÈRE", styles["KssSub"]))
        story.append(Spacer(1, 4))

        if sales_series:
            date_data = [["Date", "Chiffre d'affaires", "Nombre de commandes"]]
            for s in sales_series[:30]:  # 30 derniers jours max
                date_data.append([
                    s["day"].strftime("%d/%m/%Y"),
                    fcfa(s["total"] or 0),
                    str(s["orders"] or 0),
                ])
            date_table = Table(date_data, colWidths=[1.8 * inch, 2 * inch, 2 * inch])
            date_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ]))
            story.append(date_table)
        else:
            story.append(Paragraph("Aucune donnée disponible", styles["KssBody"]))

        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer, title="Rapport Financier", author=shop.shop_name)
        buffer.seek(0)
        filename = f"rapport-financier-{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}.pdf"
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write(buffer.read())
        return response

    def _export_orders_pdf(self, request, start, end):
        """Export PDF de la liste des commandes."""
        from io import BytesIO
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        from orders.models import Order, OrderItem
        from payments.models import Payment
        from deliveries.models import Delivery

        REVENUE_STATUSES = [Order.Status.CONFIRMED, Order.Status.PREPARING, Order.Status.SHIPPING, Order.Status.DELIVERED]

        orders = Order.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end,
            status__in=REVENUE_STATUSES
        ).prefetch_related("payments", "items")

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=25*mm, bottomMargin=25*mm)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="KssTitle", parent=styles["Title"], fontSize=16, spaceAfter=4, textColor=colors.HexColor("#111827")))
        styles.add(ParagraphStyle(name="KssBody", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#111827")))

        story = []
        story.append(Paragraph("LISTE DES COMMANDES", styles["KssTitle"]))
        story.append(Paragraph(f"Période : {start.strftime('%d/%m/%Y')} au {end.strftime('%d/%m/%Y')} | {orders.count()} commandes", styles["KssBody"]))
        story.append(Spacer(1, 6))

        # En-têtes de tableau
        headers = ["N°", "Client", "Date", "Statut", "Articles", "Sous-total", "Total", "Payé", "Solde"]
        order_data = [headers]

        for order in orders:
            # Client
            client_name = order.user.full_name if order.user else (order.customer_name or "Non spécifié")
            if len(client_name) > 25:
                client_name = client_name[:25] + "..."

            # Nombre d'articles
            item_count = order.items.count()

            # Moyens de paiement
            methods = ", ".join(sorted({p.get_method_display() for p in order.payments.all()}))
            if len(methods) > 20:
                methods = methods[:20] + "..."

            # Formatage dates
            date_str = order.created_at.strftime("%d/%m/%Y %H:%M") if order.created_at else ""

            order_data.append([
                str(order.number),
                client_name,
                date_str,
                order.get_status_display()[:15],
                str(item_count),
                fcfa(order.subtotal),
                fcfa(order.total),
                fcfa(order.amount_paid),
                fcfa(order.balance_due),
            ])

        # Ajuster les largeurs de colonnes
        col_widths = [0.5*inch, 2*inch, 1.2*inch, 1*inch, 0.6*inch, 1*inch, 1*inch, 1*inch, 1*inch]

        table = Table(order_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (5, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))

        story.append(table)
        story.append(Spacer(1, 10))

        # Résumé
        story.append(Paragraph("RÉSUMÉ", styles["KssSub"]))
        story.append(Spacer(1, 4))

        summary_data = [
            ["Total commandes", str(orders.count())],
            ["Chiffre d'affaires total", fcfa(sum(o.total for o in orders))],
            ["Total payé", fcfa(sum(o.amount_paid for o in orders))],
            ["Total solde dû", fcfa(sum(o.balance_due for o in orders))],
        ]
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ]))
        story.append(summary_table)

        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer, title=f"Commandes {start.year}", author=shop.shop_name if 'shop' in dir() else "Konaté-Service-Gym")
        buffer.seek(0)
        filename = f"list-commandes-{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}.pdf"
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write(buffer.read())
        return response

    def _export_payments_pdf(self, request, start, end):
        """Export PDF du récapitulatif des encaissements."""
        from io import BytesIO
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        from payments.models import Payment
        from orders.models import Order

        payments = Payment.objects.filter(
            status=Payment.Status.CONFIRMED, created_at__date__gte=start, created_at__date__lte=end
        ).select_related("order")

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=25*mm, bottomMargin=25*mm)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="KssTitle", parent=styles["Title"], fontSize=16, spaceAfter=4, textColor=colors.HexColor("#111827")))
        styles.add(ParagraphStyle(name="KssBody", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#111827")))

        story = []
        story.append(Paragraph("RÉCAPITULATIF DES ENCAISSEMENTS", styles["KssTitle"]))
        story.append(Paragraph(f"Période : {start.strftime('%d/%m/%Y')} au {end.strftime('%d/%m/%Y')} | {payments.count()} paiements confirmés", styles["KssBody"]))
        story.append(Spacer(1, 6))

        headers = ["Date", "Commande", "Client", "Moyen", "Montant", "Réf. OM", "Statut"]
        pay_data = [headers]

        total_amount = 0
        for p in payments:
            order_number = p.order.number[:15] if p.order.number else ""
            customer_name = p.order.customer_name[:20] if p.order.customer_name else ""
            if len(customer_name) > 20:
                customer_name = customer_name[:20] + "..."

            date_str = p.created_at.strftime("%d/%m/%Y %H:%M") if p.created_at else ""
            method_display = p.get_method_display()[:12] if p.get_method_display() else ""
            om_ref = p.om_reference or ""

            pay_data.append([
                date_str,
                order_number,
                customer_name,
                method_display,
                fcfa(p.amount),
                om_ref[:15] if om_ref else "",
                p.get_status_display()[:12],
            ])
            total_amount += p.amount

        col_widths = [1.5*inch, 1.2*inch, 2*inch, 1.5*inch, 1*inch, 1.5*inch, 1.8*inch]

        table = Table(pay_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))

        story.append(table)
        story.append(Spacer(1, 8))

        # Totaux
        story.append(Paragraph("TOTAUX", styles["KssSub"]))
        story.append(Spacer(1, 4))

        total_data = [
            ["Total encaissé", fcfa(total_amount)],
            ["Nombre de transactions", str(payments.count())],
        ]
        total_table = Table(total_data, colWidths=[4*inch, 2*inch])
        total_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ]))
        story.append(total_table)

        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer, title=f"Encaissements {start.year}", author="Konaté-Service-Gym")
        buffer.seek(0)
        filename = f"encaissements-{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}.pdf"
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write(buffer.read())
        return response

    def _export_deliveries_pdf(self, request, start, end):
        """Export PDF de la liste des livraisons."""
        from io import BytesIO
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        from deliveries.models import Delivery
        from orders.models import Order

        deliveries = Delivery.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end
        ).select_related("order")

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=25*mm, bottomMargin=25*mm)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="KssTitle", parent=styles["Title"], fontSize=16, spaceAfter=4, textColor=colors.HexColor("#111827")))
        styles.add(ParagraphStyle(name="KssBody", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#111827")))

        story = []
        story.append(Paragraph("LISTE DES LIVRAISONS", styles["KssTitle"]))
        story.append(Paragraph(f"Période : {start.strftime('%d/%m/%Y')} au {end.strftime('%d/%m/%Y')} | {deliveries.count()} livraisons", styles["KssBody"]))
        story.append(Spacer(1, 6))

        headers = ["N°", "Client", "Livreur", "Zone", "Statut", "Montant"]
        del_data = [headers]

        for d in deliveries:
            order_number = d.order.number[:12] if d.order.number else ""
            customer_name = d.customerName[:20] if d.customerName else ""
            if len(customer_name) > 20:
                customer_name = customer_name[:20] + "..."

            zone_str = d.order.delivery_district[:15] if d.order.delivery_district else "-"
            status_str = d.statusLabel[:12] if d.statusLabel else ""
            amount_str = fcfa(d.balanceDue) if d.balanceDue else "0"

            del_data.append([
                str(d.id),
                customer_name,
                d.courierName[:15] if d.courierName else "Non attribué",
                zone_str,
                status_str,
                amount_str,
            ])

        col_widths = [0.5*inch, 2.2*inch, 2*inch, 1.5*inch, 1.3*inch, 1.5*inch]

        table = Table(del_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))

        story.append(table)
        story.append(Spacer(1, 10))

        # Résumé par statut
        story.append(Paragraph("RÉSUMÉ PAR STATUT", styles["KssSub"]))
        story.append(Spacer(1, 4))

        status_summary = {}
        for d in deliveries:
            s = d.status
            status_summary[s] = status_summary.get(s, 0) + 1

        status_data = [["Statut", "Nombre"]]
        for status, count in sorted(status_summary.items()):
            status_data.append([status[:20], str(count)])

        status_table = Table(status_data, colWidths=[3*inch, 2*inch])
        status_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ]))
        story.append(status_table)

        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer, title=f"Livraisons {start.year}", author="Konaté-Service-Gym")
        buffer.seek(0)
        filename = f"list-livraisons-{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}.pdf"
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write(buffer.read())
        return response

    def _export_products_pdf(self, request, start, end):
        """Export PDF du catalogue produits avec stock."""
        from io import BytesIO
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        from catalog.models import Product, ProductVariant

        variants = ProductVariant.objects.filter(is_active=True).select_related("product")

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=25*mm, bottomMargin=25*mm)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="KssTitle", parent=styles["Title"], fontSize=16, spaceAfter=4, textColor=colors.HexColor("#111827")))
        styles.add(ParagraphStyle(name="KssBody", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#111827")))

        story = []
        story.append(Paragraph("CATALOGUE PRODUITS & STOCK", styles["KssTitle"]))
        story.append(Spacer(1, 6))

        headers = ["Produit", "Variante", "SKU", "Stock", "Seuil", "Prix achat", "Prix vente", "Valeur achat"]
        prod_data = [headers]

        for v in variants:
            product_name = v.product.name
            if len(product_name) > 25:
                product_name = product_name[:25] + "..."

            prod_data.append([
                product_name,
                v.label[:15] if len(v.label) > 15 else v.label,
                v.sku or "-",
                str(v.stock_qty),
                str(v.low_stock_threshold),
                fcfa(v.price_purchase),
                fcfa(v.price_sale),
                fcfa(v.stock_qty * v.price_purchase),
            ])

        col_widths = [2.5*inch, 1.5*inch, 1*inch, 0.8*inch, 0.8*inch, 1.2*inch, 1.2*inch, 1.3*inch]

        table = Table(prod_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))

        story.append(table)
        story.append(Spacer(1, 8))

        # Statistiques stock
        story.append(Paragraph("STATISTIQUES STOCK", styles["KssSub"]))
        story.append(Spacer(1, 4))

        low_stock = variants.filter(stock_qty__lte=F("low_stock_threshold"))
        total_value = sum(v.stock_qty * v.price_purchase for v in variants)

        stock_stats = [
            ["Valeur totale du stock", fcfa(total_value)],
            ["Variantes en stock", str(variants.count())],
            ["En rupture / faible stock", str(low_stock.count())],
            ["Seuil bas activé", "OUI" if low_stock.count() > 0 else "NON"],
        ]
        stock_table = Table(stock_data if False else stock_stats, colWidths=[4*inch, 2*inch])
        # Recreate
        story_table = Table(stock_stats, colWidths=[3*inch, 3*inch])
        story_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ]))
        story.append(story_table)

        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer, title=f"Catalogue produits {start.year}", author="Konaté-Service-Gym")
        buffer.seek(0)
        filename = f"catalogue-produits-{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}.pdf"
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write(buffer.read())
        return response

    @staticmethod
    def _header_footer(canvas, doc, title, shop=None):
        """En-tête et pied de page PDF."""
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(colors.HexColor("#111827"))
        canvas.rect(0, height - 25 * mm, width, 25 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(20 * mm, height - 12 * mm, title or "Konaté-Service-Gym")
        canvas.drawRightString(width - 20 * mm, height - 12 * mm, f"{timezone.localtime().strftime('%d/%m/%Y %H:%M')}")
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.setFont("Helvetica", 7)
        footer_text = f"{title or 'Rapports'} — Konaté-Service-Gym"
        canvas.drawCentredString(width / 2, 12 * mm, footer_text)
        canvas.restoreState()


def fcfa(amount):
    return f"{int(amount or 0):,} FCFA".replace(",", " ")