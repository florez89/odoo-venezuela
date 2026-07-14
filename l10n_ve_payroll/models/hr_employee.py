# -*- coding: utf-8 -*-
from odoo import api, fields, models

class HrVersion(models.Model):
    _inherit = 'hr.version'

    wage_currency_id = fields.Many2one(
        'res.currency',
        string="Moneda Pactada",
        default=lambda self: self.env.company.currency_id,
        required=True,
        help="Moneda en la que se pacta el sueldo básico del empleado."
    )
    wage_in_currency = fields.Float(
        string="Sueldo Pactado",
        required=True,
        default=0.0,
        digits=(16, 2),
        help="Monto del sueldo básico en la moneda pactada."
    )
    wage = fields.Monetary(
        compute="_compute_wage",
        store=True,
        readonly=False,
        help="Sueldo básico convertido a la moneda de la compañía (VES)."
    )

    @api.depends('wage_in_currency', 'wage_currency_id', 'date_version')
    def _compute_wage(self):
        for version in self:
            if version.wage_currency_id and version.wage_in_currency:
                company = version.company_id or self.env.company
                # Convert using the rate at date_version (or today if not set)
                date = version.date_version or fields.Date.context_today(self)
                version.wage = version.wage_currency_id._convert(
                    version.wage_in_currency,
                    company.currency_id,
                    company,
                    date
                )
            else:
                version.wage = version.wage_in_currency


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    wage_currency_id = fields.Many2one(
        'res.currency',
        related='version_id.wage_currency_id',
        readonly=False,
        string="Moneda Pactada",
        help="Moneda en la que se pacta el sueldo básico del empleado."
    )
    wage_in_currency = fields.Float(
        related='version_id.wage_in_currency',
        readonly=False,
        string="Sueldo Pactado",
        help="Monto del sueldo básico en la moneda pactada."
    )
