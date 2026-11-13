from odoo import api, models
from odoo.tools.misc import formatLang

import logging

_logger = logging.getLogger(__name__)


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.model
    def _get_tax_totals_summary(self, base_lines, currency, company, cash_rounding=None):
        """
        Add the foreign (alternate) currency amounts to the tax totals summary.

        The summary is computed twice by the parent method: once for the document currency and
        once for the foreign currency of the company, using the foreign prices of the lines.

        Besides the Odoo 18 keys, the result keeps the keys the Venezuelan modules used with the
        Odoo 17 summary (``amount_untaxed``, ``amount_total``, ``groups_by_subtotal``,
        ``foreign_amount_untaxed``, ``foreign_amount_total``, ``groups_by_foreign_subtotal``,
        ``foreign_subtotals``, ``subtotal``, ``discount_amount``...), so reports and other modules
        reading them keep working. The full foreign summary is available under
        ``foreign_tax_totals`` for the foreign totals widget.
        """
        res = super()._get_tax_totals_summary(base_lines, currency, company, cash_rounding=cash_rounding)

        company = company or self.env.company
        foreign_currency = company.foreign_currency_id
        if not foreign_currency:
            # Odoo 18 also uses this summary to compute the amounts of orders and invoices
            # (e.g. purchase.order._amount_all), so a company without foreign currency gets
            # the summary with zero foreign amounts instead of an error.
            self._add_ve_tax_totals_keys(res, currency, self._get_tax_totals_without_discount(
                res, base_lines, currency, company))
            res.update(self._get_empty_foreign_tax_totals_keys())
            return res

        foreign_base_lines = self._prepare_foreign_base_lines_for_tax_totals(
            base_lines, foreign_currency, company
        )
        foreign_res = super()._get_tax_totals_summary(
            foreign_base_lines, foreign_currency, company, cash_rounding=cash_rounding
        )

        res_without_discount = self._get_tax_totals_without_discount(
            res, base_lines, currency, company
        )
        foreign_res_without_discount = self._get_tax_totals_without_discount(
            foreign_res, foreign_base_lines, foreign_currency, company
        )

        self._add_ve_tax_totals_keys(res, currency, res_without_discount)
        self._add_ve_tax_totals_keys(foreign_res, foreign_currency, foreign_res_without_discount)

        for subtotal, foreign_subtotal in zip(res["subtotals"], foreign_res["subtotals"]):
            subtotal["base_amount_foreign_currency"] = foreign_subtotal["base_amount_currency"]
            subtotal["tax_amount_foreign_currency"] = foreign_subtotal["tax_amount_currency"]
            for tax_group, foreign_tax_group in zip(
                subtotal["tax_groups"], foreign_subtotal["tax_groups"]
            ):
                tax_group["base_amount_foreign_currency"] = foreign_tax_group["base_amount_currency"]
                tax_group["tax_amount_foreign_currency"] = foreign_tax_group["tax_amount_currency"]

        res.update(
            {
                "foreign_currency_id": foreign_currency.id,
                "base_amount_foreign_currency": foreign_res["base_amount_currency"],
                "tax_amount_foreign_currency": foreign_res["tax_amount_currency"],
                "total_amount_foreign_currency": foreign_res["total_amount_currency"],
                "foreign_tax_totals": foreign_res,
                # Keys of the Odoo 17 summary in foreign currency.
                "groups_by_foreign_subtotal": foreign_res["groups_by_subtotal"],
                "foreign_subtotals": foreign_res["subtotals"],
                "foreign_amount_untaxed": foreign_res["amount_untaxed"],
                "foreign_amount_total": foreign_res["amount_total"],
                "foreign_formatted_amount_untaxed": foreign_res["formatted_amount_untaxed"],
                "foreign_formatted_amount_total": foreign_res["formatted_amount_total"],
                "foreign_subtotal": foreign_res["subtotal"],
                "foreign_formatted_subtotal": foreign_res["formatted_subtotal"],
                "foreign_discount_amount": foreign_res["discount_amount"],
                "foreign_formatted_discount_amount": foreign_res["formatted_discount_amount"],
            }
        )
        return res

    @api.model
    def _get_tax_totals_without_discount(self, tax_totals, base_lines, currency, company):
        """Summary of the base lines without their discount (``tax_totals`` when no line has
        a discount)."""
        if not any(base_line.get("discount") for base_line in base_lines):
            return tax_totals
        # Call the standard summary: only the amounts are needed.
        return super()._get_tax_totals_summary(
            self._prepare_base_lines_without_discount(base_lines, company), currency, company
        )

    @api.model
    def _get_empty_foreign_tax_totals_keys(self):
        return {
            "foreign_currency_id": False,
            "base_amount_foreign_currency": 0.0,
            "tax_amount_foreign_currency": 0.0,
            "total_amount_foreign_currency": 0.0,
            "foreign_tax_totals": False,
            "groups_by_foreign_subtotal": {},
            "foreign_subtotals": [],
            "foreign_amount_untaxed": 0.0,
            "foreign_amount_total": 0.0,
            "foreign_formatted_amount_untaxed": "",
            "foreign_formatted_amount_total": "",
            "foreign_subtotal": 0.0,
            "foreign_formatted_subtotal": "",
            "foreign_discount_amount": 0.0,
            "foreign_formatted_discount_amount": "",
        }

    @api.model
    def _prepare_foreign_base_lines_for_tax_totals(self, base_lines, foreign_currency, company):
        """
        Build the base lines used to compute the tax totals in the foreign currency.

        Lines whose record has a ``foreign_price`` use it as unit price, the other special lines
        (early payment discount, cash rounding) are converted with the foreign inverse rate of
        their record when available.
        """
        foreign_base_lines = []
        for base_line in base_lines:
            record = base_line.get("record")
            price_unit = base_line["price_unit"]
            line_currency = base_line["currency_id"]
            if isinstance(record, models.BaseModel) and "foreign_price" in record._fields:
                line_currency = foreign_currency
                if base_line.get("special_type") in ("early_payment", "cash_rounding"):
                    price_unit = price_unit * (record.foreign_inverse_rate or 0.0)
                else:
                    price_unit = record.foreign_price
            foreign_base_lines.append(
                {
                    **base_line,
                    "price_unit": price_unit,
                    "currency_id": line_currency,
                    "rate": 1.0,
                    "manual_total_excluded_currency": None,
                    "manual_total_excluded": None,
                    "manual_tax_amounts": None,
                }
            )
        self._add_tax_details_in_base_lines(foreign_base_lines, company)
        self._round_base_lines_tax_details(foreign_base_lines, company)
        return foreign_base_lines

    @api.model
    def _prepare_base_lines_without_discount(self, base_lines, company):
        base_lines_without_discount = [
            {
                **base_line,
                "discount": 0.0,
                "manual_total_excluded_currency": None,
                "manual_total_excluded": None,
                "manual_tax_amounts": None,
            }
            for base_line in base_lines
        ]
        self._add_tax_details_in_base_lines(base_lines_without_discount, company)
        self._round_base_lines_tax_details(base_lines_without_discount, company)
        return base_lines_without_discount

    @api.model
    def _add_ve_tax_totals_keys(self, tax_totals, currency, tax_totals_without_discount):
        """Add to an Odoo 18 tax totals summary the keys of the Odoo 17 summary used by the
        Venezuelan modules, expressed in ``currency``."""

        def fmt(amount):
            return formatLang(self.env, amount, currency_obj=currency)

        amount_untaxed = tax_totals["base_amount_currency"]
        amount_total = tax_totals["total_amount_currency"]
        groups_by_subtotal = {}
        for subtotal in tax_totals["subtotals"]:
            subtotal["amount"] = subtotal["base_amount_currency"]
            subtotal["formatted_amount"] = fmt(subtotal["base_amount_currency"])
            groups_by_subtotal[subtotal["name"]] = [
                {
                    "group_key": tax_group["id"],
                    "tax_group_id": tax_group["id"],
                    "tax_group_name": tax_group["group_name"],
                    "tax_group_amount": tax_group["tax_amount_currency"],
                    "tax_group_base_amount": tax_group["base_amount_currency"],
                    "formatted_tax_group_amount": fmt(tax_group["tax_amount_currency"]),
                    "formatted_tax_group_base_amount": fmt(tax_group["base_amount_currency"]),
                    "hide_base_amount": tax_group["display_base_amount_currency"] is False,
                }
                for tax_group in subtotal["tax_groups"]
            ]

        subtotal_without_discount = tax_totals_without_discount["base_amount_currency"]
        discount_amount = amount_untaxed - subtotal_without_discount
        tax_totals.update(
            {
                "amount_untaxed": amount_untaxed,
                "amount_total": amount_total,
                "formatted_amount_untaxed": fmt(amount_untaxed),
                "formatted_amount_total": fmt(amount_total),
                "groups_by_subtotal": groups_by_subtotal,
                "subtotals_order": list(groups_by_subtotal),
                "display_tax_base": not tax_totals.get("same_tax_base", True),
                "show_discount": self.env.company.show_discount_on_moves,
                "subtotal": subtotal_without_discount,
                "formatted_subtotal": fmt(subtotal_without_discount),
                "discount_amount": discount_amount,
                "formatted_discount_amount": fmt(discount_amount),
            }
        )
        if "cash_rounding_base_amount_currency" in tax_totals:
            tax_totals["formatted_amount_total_rounded"] = fmt(amount_total)
        return tax_totals
