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
        before = {company: company.foreign_currency_id for company in self}
        res = super().write(vals)
        aml_model = self.env.get("account.move.line")
        if (
            "foreign_currency_id" not in vals
            or aml_model is None
            or "foreign_currency_id" not in aml_model._fields
        ):
            return res
        for company, before_currency in before.items():
            # Only a real change of an already used currency is forbidden;
            # re-writing the same value (e.g. saving the settings) is allowed.
            if not before_currency or company.foreign_currency_id == before_currency:
                continue
            if aml_model.search_count(
                [
                    ("foreign_currency_id", "=", before_currency.id),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            ):
                raise ValidationError(
                    _(
                        "The currency already has accounting movements, you cannot deactivate this foreign currency"
                    )
                )
        return res

    @api.constrains("foreign_currency_id", "currency_id")
    def _check_foreign_currency_id(self):
        for rec in self:
            if "currency_id" in rec._fields and rec.currency_id == rec.foreign_currency_id:
                raise UserError(
                    _("The currency foreign must be different from the currency of the company")
                )
