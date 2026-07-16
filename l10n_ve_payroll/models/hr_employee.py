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
    l10n_ve_prestaciones_balance = fields.Float(
        string='Acumulado Prestaciones',
        compute='_compute_l10n_ve_prestaciones_totals',
        digits=(16, 2),
        help="Saldo total acumulado de las prestaciones sociales."
    )
    l10n_ve_prestaciones_interest = fields.Float(
        string='Intereses Acumulados',
        compute='_compute_l10n_ve_prestaciones_totals',
        digits=(16, 2),
        help="Total de intereses generados sobre prestaciones."
    )
    l10n_ve_prestaciones_ledger_ids = fields.One2many(
        'l10n_ve.prestaciones.ledger',
        'employee_id',
        string='Registros de Prestaciones'
    )

    def _compute_l10n_ve_prestaciones_totals(self):
        for employee in self:
            latest_ledger = self.env['l10n_ve.prestaciones.ledger'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'posted')
            ], order='date desc', limit=1)
            if latest_ledger:
                employee.l10n_ve_prestaciones_balance = latest_ledger.accumulated_balance
                employee.l10n_ve_prestaciones_interest = latest_ledger.accumulated_interest
            else:
                employee.l10n_ve_prestaciones_balance = 0.0
                employee.l10n_ve_prestaciones_interest = 0.0
