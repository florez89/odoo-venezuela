from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_round


class PosOrder(models.Model):
    _inherit = "pos.order"

    # The PoS sends both with the order (pos.order loads and serializes all its
    # fields). amount_total is the invoice total, without the IGTF; amount_paid
    # includes it (the payment lines of an IGTF method are base + IGTF).
    igtf_amount = fields.Float()
    bi_igtf = fields.Float()

    def _get_total_with_igtf(self):
        self.ensure_one()
        return self.currency_id.round(self.amount_total + self.igtf_amount)

    def action_pos_order_paid(self):
        self.ensure_one()
        if self.currency_id.is_zero(self.igtf_amount):
            return super().action_pos_order_paid()
        # Same check as point_of_sale (no hook for the total to compare) against
        # the total the customer pays: invoice total + IGTF.
        total_with_igtf = self._get_total_with_igtf()
        config = self.config_id
        if not config.cash_rounding or (
            config.only_round_cash_method
            and not any(p.payment_method_id.is_cash_count for p in self.payment_ids)
        ):
            total = total_with_igtf
        else:
            total = float_round(
                total_with_igtf,
                precision_rounding=config.rounding_method.rounding,
                rounding_method=config.rounding_method.rounding_method,
            )
        if not float_is_zero(total - self.amount_paid, precision_rounding=self.currency_id.rounding):
            if not config.cash_rounding:
                raise UserError(_("Order %s is not fully paid.", self.name))
            if config.rounding_method.rounding_method == "HALF-UP":
                max_diff = self.currency_id.round(config.rounding_method.rounding / 2)
            else:
                max_diff = self.currency_id.round(config.rounding_method.rounding)
            if abs(self.currency_id.round(total_with_igtf - self.amount_paid)) > max_diff:
                raise UserError(_("Order %s is not fully paid.", self.name))
        self.write({"state": "paid"})
        return True

    def _is_pos_order_paid(self):
        if self.currency_id.is_zero(self.igtf_amount):
            return super()._is_pos_order_paid()
        amount_total = self._get_total_with_igtf()
        if float_is_zero(
            self.refunded_order_id.amount_total + amount_total,
            precision_rounding=self.currency_id.rounding,
        ):
            amount_total = -self.refunded_order_id.amount_paid
        return float_is_zero(
            self._get_rounded_amount(amount_total) - self.amount_paid,
            precision_rounding=self.currency_id.rounding,
        )

    def _create_invoice(self, move_vals):
        res = super()._create_invoice(move_vals)
        res.write({"bi_igtf": abs(self.bi_igtf)})
        return res
