from odoo import models, fields, api
from odoo.tools import float_compare
import logging

_logger = logging.getLogger(__name__)


class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    @api.model
    def compute_rate(self, foreign_currency_id, rate_date, with_rate_date=False):
        """
        Compute the rate and inverse rate for the given currency and date.

        If the foreign currency is USD then the rate will be the inverse company rate and the
        inverse rate will be the company rate, Else both rates will be the company rate.

        This is done because the foreign rate will be the rate that is gonna be shown to the user
        and the inverse rate will be the rate that will be used as factor to multiply for the
        computation of the foreign amounts.

        The logic is that if the foreign currency is VEF then we will be always multiplying by the
        value the user uses and see as the rate, but if the foreign currency is USD then we will be
        always multiplying by the inverse rate because the user will see the rate as the inverse
        rate.

        Parameters
        ----------
        foreign_currency_id : int
            The id of the foreign currency.
        rate_date : date
            The date of the rate that is gonna be searched for the given currency
            (foreign_currency_id).
        with_rate_date : bool
            Whether to add `rate_date`, the date of the rate used, to the result.
            Off by default: several callers write the result straight into
            records (`record.update(rate_values)`).

        The rate used is the one in force on `rate_date`: the latest dated on or
        before it. When the currency has no rate up to that date, the earliest
        later rate is used (like native Odoo) and `rate_date` is that rate's date.
        Each document checks the age of the rate with `rate_date` and
        `res.company.rate_max_age_days`.

        Returns
        -------
        dict
            A dictionary with the rate and inverse rate for the given currency and
            date (plus `rate_date` with with_rate_date=True), or {} when the
            currency has no rate at all.
        """
        rates = self.env["res.currency.rate"].search(
            [
                ("currency_id", "=", foreign_currency_id),
                ("company_id", "=", self.env.company.id),
                ("name", "<=", rate_date),
            ], order='name desc', limit=1
        )
        if not rates:
            rates = self.env['res.currency.rate'].search([
                ("currency_id", "=", foreign_currency_id),
                ("company_id", "=", self.env.company.id),
            ], order='name asc', limit=1)
        if not rates:
            return {}
        rate = rates[0]
        base_usd_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "base.USD", raise_if_not_found=False
        )
        if foreign_currency_id == base_usd_id:
            values = {
                "foreign_rate": rate.inverse_company_rate,
                "foreign_inverse_rate": rate.company_rate,
            }
        else:
            values = {"foreign_rate": rate.company_rate, "foreign_inverse_rate": rate.company_rate}
        if with_rate_date:
            values["rate_date"] = rate.name
        return values

    @api.model
    def get_rate_in_force_date(self, foreign_currency_id, rate_date, foreign_inverse_rate):
        """Return the date of the rate in force on `rate_date` when a document
        uses it (same `foreign_inverse_rate`), or False.

        A document whose rate does not match the one in force (typed by hand or
        taken from another date on purpose, like a payment registered with the
        invoice rate) has no rate in force to age, so it never warns.
        """
        if not foreign_currency_id or not foreign_inverse_rate:
            return False
        values = self.compute_rate(foreign_currency_id, rate_date, with_rate_date=True)
        if not values.get("rate_date") or float_compare(
            values["foreign_inverse_rate"], foreign_inverse_rate, precision_digits=10
        ):
            return False
        return values["rate_date"]

    @api.model
    def compute_inverse_rate(self, rate):
        """
        Compute the inverse rate for the given rate.
        The inverse rate will be the inverse of the given rate if the foreign currency is USD, else
        the inverse rate will be the same as the given rate.

        Parameters
        ----------
        rate : float
            The rate that is gonna be used to compute the inverse rate.

        Returns
        -------
        float
            The inverse rate for the given rate.
        """
        base_usd_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "base.USD", raise_if_not_found=False
        )
        foreign_currency_id = self.env.company.foreign_currency_id.id or False
        inverse_rate = 1 / rate if foreign_currency_id == base_usd_id else rate
        return inverse_rate
