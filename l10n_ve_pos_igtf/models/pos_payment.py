from odoo import api, fields, models, _
from odoo.tools import float_is_zero
from odoo.tools.float_utils import float_round

import logging

_logger = logging.getLogger(__name__)


class PosPayment(models.Model):
    _inherit = "pos.payment"

    # Sent by the PoS with the payment (pos.payment loads and serializes all its fields).
    include_igtf = fields.Boolean()
    igtf_amount = fields.Float()
    foreign_igtf_amount = fields.Float()

    def _create_payment_moves(self, is_reverse=False):
        """Invoice payment entries of the payments that include IGTF: the
        receivable of the customer is credited with the base and the IGTF account
        of the company with the IGTF. The other payments follow the standard
        flow."""
        igtf_payments = self.filtered(
            lambda p: p.include_igtf
            and not float_is_zero(p.igtf_amount, precision_rounding=p.currency_id.rounding)
            and p.payment_method_id.type != "pay_later"
        )
        # Positional: pos_no_followup overrides the method with another argument name.
        result = super(PosPayment, self - igtf_payments)._create_payment_moves(is_reverse)
        credit_line_ids = list(result._context.get("credit_line_ids") or [])
        igtf_moves = self.env["account.move"]
        for payment in igtf_payments:
            move, credit_lines = payment._create_igtf_payment_move(is_reverse)
            igtf_moves |= move
            credit_line_ids += credit_lines.ids
        return (result | igtf_moves).with_context(credit_line_ids=credit_line_ids)

    def _create_igtf_payment_move(self, is_reverse=False):
        self.ensure_one()
        order = self.pos_order_id
        payment_method = self.payment_method_id
        accounting_partner = self.env["res.partner"]._find_accounting_partner(self.partner_id)
        pos_session = order.session_id
        journal = pos_session.config_id.journal_id
        Rate = self.env["res.currency.rate"]
        move_vals = {
            "journal_id": journal.id,
            "date": fields.Date.context_today(order, order.date_order),
            "ref": _(
                "Invoice payment for %(order)s (%(account_move)s) using %(payment_method)s",
                order=order.name,
                account_move=order.account_move.name,
                payment_method=payment_method.name,
            ),
            "pos_payment_ids": self.ids,
        }
        if self.foreign_rate:
            move_vals.update(
                {
                    "foreign_rate": self.foreign_rate,
                    "foreign_inverse_rate": Rate.compute_inverse_rate(self.foreign_rate),
                    "manually_set_rate": True,
                }
            )
        payment_move = (
            self.env["account.move"].with_context(default_journal_id=journal.id).create(move_vals)
        )
        self.write({"account_move_id": payment_move.id})

        rounding = self.currency_id.rounding
        amounts = pos_session._update_amounts(
            {"amount": 0, "amount_converted": 0}, {"amount": self.amount}, self.payment_date
        )
        amount_igtf = float_round(self.igtf_amount, precision_rounding=rounding)
        foreign_igtf = self.foreign_igtf_amount
        foreign_base = self.foreign_amount - foreign_igtf
        receivable_account = accounting_partner.with_company(
            order.company_id
        ).property_account_receivable_id

        def foreign_values(foreign_amount, credit=True):
            if credit == (foreign_amount > 0):
                return {"foreign_credit": abs(foreign_amount), "foreign_debit": 0.0}
            return {"foreign_debit": abs(foreign_amount), "foreign_credit": 0.0}

        line_vals = []
        base_amount = amounts["amount"] - amount_igtf
        if not float_is_zero(base_amount, precision_rounding=rounding):
            line_vals.append(
                pos_session._credit_amounts(
                    {
                        "account_id": receivable_account.id,
                        "partner_id": accounting_partner.id,
                        "move_id": payment_move.id,
                        "not_foreign_recalculate": True,
                        **foreign_values(foreign_base),
                    },
                    base_amount,
                    amounts["amount_converted"] - amount_igtf,
                )
            )
        line_vals.append(
            pos_session._credit_amounts(
                {
                    "account_id": self.company_id.customer_account_igtf_id.id,
                    "partner_id": accounting_partner.id,
                    "move_id": payment_move.id,
                    "not_foreign_recalculate": True,
                    **foreign_values(foreign_igtf),
                },
                amount_igtf,
                amount_igtf,
            )
        )
        is_split_transaction = payment_method.split_transactions
        if is_split_transaction and is_reverse:
            reversed_move_receivable_account_id = receivable_account.id
        elif is_reverse:
            reversed_move_receivable_account_id = (
                payment_method.receivable_account_id.id
                or self.company_id.account_default_pos_receivable_account_id.id
            )
        else:
            reversed_move_receivable_account_id = (
                self.company_id.account_default_pos_receivable_account_id.id
            )
        line_vals.append(
            pos_session._debit_amounts(
                {
                    "account_id": reversed_move_receivable_account_id,
                    "move_id": payment_move.id,
                    "partner_id": accounting_partner.id
                    if is_split_transaction and is_reverse
                    else False,
                    "not_foreign_recalculate": True,
                    **foreign_values(self.foreign_amount, credit=False),
                },
                amounts["amount"],
                amounts["amount_converted"],
            )
        )
        lines = self.env["account.move.line"].with_context(check_move_validity=False).create(
            line_vals
        )
        payment_move._post()
        credit_lines = lines.filtered(
            lambda l: l.account_id == receivable_account
            and (l.debit if amounts["amount_converted"] < 0 else l.credit)
        )
        return payment_move, credit_lines
