from odoo import api, fields, models, _
from odoo.tools import format_date

import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def default_alternate_currency(self):
        """
        This method is used to get the foreign currency of the company and set it as the default
        value of the foreign currency field.

        Returns
        -------
        type = int
            The id of the foreign currency of the company
        """
        return self.env.company.foreign_currency_id.id or False

    foreign_currency_id = fields.Many2one(
        "res.currency", default=default_alternate_currency
    )

    # No default: a default stops the compute when the payment is created (from code or
    # from the form), leaving the payment without rate (rate 0).
    foreign_rate = fields.Float(
        compute="_compute_rate",
        digits="Tasa",
        store=True,
        readonly=False,
    )
    foreign_inverse_rate = fields.Float(
        help="Rate that will be used as factor to multiply of the foreign currency for this move.",
        compute="_compute_rate",
        digits=(16, 15),
        store=True,
        readonly=False,
    )

    foreign_rate_date = fields.Date(
        string="Rate Used Date",
        compute="_compute_foreign_rate_age",
        help="Date of the rate in force used by the payment. Empty when its rate "
        "was set on purpose (typed by hand or taken from the invoice date).",
    )
    foreign_rate_age_days = fields.Integer(
        string="Rate Age (Days)",
        compute="_compute_foreign_rate_age",
    )
    is_foreign_rate_outdated = fields.Boolean(
        string="Outdated Rate",
        compute="_compute_foreign_rate_age",
        help="The rate is older than the company's maximum rate age: confirming "
        "the payment from the form asks for confirmation.",
    )

    concept = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override the create method to set the rate of the payment to its move.
        """
        payments = super().create(vals_list)
        for payment in payments.with_context(skip_account_move_synchronization=True):
            payment.move_id.write(
                {
                    "foreign_rate": payment.foreign_rate,
                    "foreign_inverse_rate": payment.foreign_inverse_rate,
                }
            )
        return payments

    def _generate_move_vals(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        """
        Odoo 18 creates the journal entry of the payment from these values (the payment no longer
        inherits from its move), so the rates of the payment must be part of them: the lines are
        converted with the rate of the move while it is created.
        """
        vals = super()._generate_move_vals(write_off_line_vals, force_balance, line_ids)
        vals.update(
            {
                "foreign_rate": self.foreign_rate,
                "foreign_inverse_rate": self.foreign_inverse_rate,
            }
        )
        return vals

    def _synchronize_to_moves(self, changed_fields):
        """
        Override the _syncrhonize_to_moves method to set the rate of the payment to its move.
        """
        res = super()._synchronize_to_moves(changed_fields)
        if not (
            "foreign_rate" in changed_fields or "foreign_inverse_rate" in changed_fields
        ):
            return
        for payment in self.with_context(skip_account_move_synchronization=True):
            payment.move_id.write(
                {
                    "foreign_rate": payment.foreign_rate,
                    "foreign_inverse_rate": payment.foreign_inverse_rate,
                }
            )
        return res

    @api.depends("date")
    def _compute_rate(self):
        """
        Compute the rate of the payment using the compute_rate method of the res.currency.rate model.
        """
        Rate = self.env["res.currency.rate"]
        for payment in self:
            rate_values = Rate.compute_rate(
                payment.foreign_currency_id.id, payment.date or fields.Date.today()
            )
            payment.update(rate_values)

    @api.depends("date", "foreign_currency_id", "foreign_inverse_rate", "company_id.rate_max_age_days")
    def _compute_foreign_rate_age(self):
        Rate = self.env["res.currency.rate"]
        for payment in self:
            # same date as _compute_rate
            payment_date = payment.date or fields.Date.today()
            rate_date = Rate.with_company(payment.company_id).get_rate_in_force_date(
                payment.foreign_currency_id.id, payment_date, payment.foreign_inverse_rate
            )
            age = (payment_date - rate_date).days if rate_date else 0
            limit = payment.company_id.rate_max_age_days
            payment.foreign_rate_date = rate_date
            payment.foreign_rate_age_days = age
            payment.is_foreign_rate_outdated = bool(limit and age > limit)

    def action_post(self):
        # `l10n_ve_check_rate_age` comes from the form's Confirm button only:
        # code posting payments (automatic flows) is never stopped.
        if self.env.context.get("l10n_ve_check_rate_age") and not self.env.context.get(
            "l10n_ve_rate_age_confirmed"
        ):
            if self.filtered("is_foreign_rate_outdated"):
                return {
                    "name": _("Outdated Exchange Rate"),
                    "type": "ir.actions.act_window",
                    "res_model": "account.payment.rate.age.wizard",
                    "view_mode": "form",
                    "target": "new",
                    "context": {"default_payment_ids": self.ids},
                }
        outdated = {
            payment: (payment.foreign_rate_date, payment.foreign_rate_age_days)
            for payment in self
            if payment.is_foreign_rate_outdated
        }
        res = super().action_post()
        for payment, (rate_date, age) in outdated.items():
            payment.message_post(
                body=_(
                    "Posted by %(user)s with the exchange rate of %(rate_date)s, %(age)s days old.",
                    user=self.env.user.name,
                    rate_date=format_date(self.env, rate_date),
                    age=age,
                )
            )
        return res

    @api.onchange("foreign_rate")
    def _onchange_foreign_rate(self):
        """
        Onchange the foreign rate and compute the foreign inverse rate
        """
        Rate = self.env["res.currency.rate"]
        for payment in self:
            if not bool(payment.foreign_rate):
                return
            payment.foreign_inverse_rate = Rate.compute_inverse_rate(
                payment.foreign_rate
            )

    # @api.model
    # def _get_trigger_fields_to_synchronize(self):
    #     original_fields = super()._get_trigger_fields_to_synchronize()
    #     additional_fields = ("foreign_rate", "foreign_inverse_rate")
    #     return original_fields + additional_fields
