from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    foreign_currency_id = fields.Many2one("res.currency", related="company_id.foreign_currency_id")
    foreign_amount_total = fields.Float(string="Foreign Total", readonly=True, required=True, default=0.0)
    # Rate shown to the user (VEF per USD) when the order was created; the PoS
    # sends it with the order (pos.order loads and serializes all its fields).
    foreign_currency_rate = fields.Float(readonly=True, required=False)

    def _prepare_invoice_vals(self):
        self.ensure_one()
        res = super()._prepare_invoice_vals()
        if self.foreign_currency_rate:
            res.update(
                {
                    "foreign_rate": self.foreign_currency_rate,
                    "foreign_inverse_rate": self.env["res.currency.rate"].compute_inverse_rate(
                        self.foreign_currency_rate
                    ),
                    "manually_set_rate": True,
                }
            )
        return res

    def get_payments_order_refund(self):
        return self.payment_ids.read(
            ["payment_method_id", "display_name", "amount", "foreign_amount"]
        )

    @api.model
    def _get_invoice_lines_values(self, line_values, pos_order_line):
        res = super()._get_invoice_lines_values(line_values, pos_order_line)
        res["foreign_price"] = pos_order_line.foreign_price
        return res


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    foreign_currency_rate = fields.Float(related="order_id.foreign_currency_rate")
    foreign_price = fields.Float(readonly=True)

    @api.model
    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)
        return res + [name for name in ("foreign_price",) if name not in res]

    def _prepare_refund_data(self, refund_order, PosOrderLineLot):
        res = super()._prepare_refund_data(refund_order, PosOrderLineLot)
        res.update({"foreign_price": self.foreign_price})
        return res
