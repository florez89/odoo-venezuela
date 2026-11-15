from odoo import api, fields, models


class AccountPaymentRateAgeWizard(models.TransientModel):
    _name = "account.payment.rate.age.wizard"
    _description = "Confirm Payment With Outdated Rate"

    payment_ids = fields.Many2many("account.payment")
    outdated_payment_ids = fields.Many2many(
        "account.payment", compute="_compute_outdated_payment_ids"
    )

    @api.depends("payment_ids")
    def _compute_outdated_payment_ids(self):
        for wizard in self:
            wizard.outdated_payment_ids = wizard.payment_ids.filtered("is_foreign_rate_outdated")

    def action_confirm(self):
        self.payment_ids.with_context(l10n_ve_rate_age_confirmed=True).action_post()
        return {"type": "ir.actions.act_window_close"}
