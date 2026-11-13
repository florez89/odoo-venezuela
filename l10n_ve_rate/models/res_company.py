from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    foreign_currency_id = fields.Many2one(
        "res.currency",
        string="Foreign Currency",
        help="Foreign currency for the company",
    )
    rate_max_age_days = fields.Integer(
        string="Maximum Rate Age (Days)",
        default=2,
        help="A document whose exchange rate is older than this number of days "
        "shows a warning and asks for confirmation before it is posted. "
        "0 disables the warning.",
    )

    @api.constrains("rate_max_age_days")
    def _check_rate_max_age_days(self):
        if any(company.rate_max_age_days < 0 for company in self):
            raise ValidationError(_("The maximum rate age cannot be negative."))

    def write(self, vals):
        before_currency = self.foreign_currency_id
        res = super().write(vals)
        if "foreign_currency_id" in vals and before_currency:
            lines = self.env["account.move.line"].search(
                [("foreign_currency_id", "=", before_currency.id)]
            )
            if lines:
                raise ValidationError(
                    _(
                        "The currency already has accounting movements, you cannot deactivate this foreign currency"
                    )
                )
        return res
