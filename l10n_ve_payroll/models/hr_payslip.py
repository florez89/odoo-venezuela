# -*- coding: utf-8 -*-
from odoo import api, fields, models

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    l10n_ve_bcv_rate = fields.Float(
        string="Tasa BCV (VES/USD)",
        compute="_compute_l10n_ve_bcv_rate",
        store=True,
        readonly=False,
        digits=(16, 4),
        help="Tipo de cambio oficial BCV (VES por USD) a la fecha de fin del periodo."
    )
    wage_in_currency = fields.Float(
        string="Sueldo Pactado",
        compute="_compute_wage_in_ves",
        store=True,
        digits=(16, 2),
        help="Monto del sueldo pactado original del empleado."
    )
    wage_in_ves = fields.Float(
        string="Sueldo en VES (Tasa BCV)",
        compute="_compute_wage_in_ves",
        store=True,
        digits=(16, 2),
        help="Sueldo base convertido a bolívares usando la tasa BCV del periodo."
    )

    @api.depends('date_to', 'employee_id')
    def _compute_l10n_ve_bcv_rate(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for payslip in self:
            if not usd:
                payslip.l10n_ve_bcv_rate = 1.0
                continue
            company = payslip.company_id or self.env.company
            date = payslip.date_to or fields.Date.context_today(self)
            # Convert 1 USD to VES using Odoo's native convert method
            rate = usd._convert(1.0, company.currency_id, company, date)
            payslip.l10n_ve_bcv_rate = rate

    @api.depends('employee_id', 'l10n_ve_bcv_rate')
    def _compute_wage_in_ves(self):
        for payslip in self:
            employee = payslip.employee_id
            if employee:
                payslip.wage_in_currency = employee.wage_in_currency
                if employee.wage_currency_id.name == 'USD':
                    payslip.wage_in_ves = employee.wage_in_currency * payslip.l10n_ve_bcv_rate
                else:
                    payslip.wage_in_ves = employee.wage_in_currency
            else:
                payslip.wage_in_currency = 0.0
                payslip.wage_in_ves = 0.0

    def _get_mondays_in_period(self, date_from, date_to):
        if not date_from or not date_to:
            return 0
        from datetime import timedelta
        d_from = fields.Date.from_string(date_from)
        d_to = fields.Date.from_string(date_to)
        
        mondays = 0
        curr = d_from
        while curr <= d_to:
            if curr.weekday() == 0:  # Monday is 0
                mondays += 1
            curr += timedelta(days=1)
        return mondays

    def _get_active_ve_parameter(self):
        self.ensure_one()
        date = self.date_to or fields.Date.context_today(self)
        return self.env['l10n_ve.payroll.parameter'].search([
            ('date_start', '<=', date),
            ('date_end', '>=', date)
        ], limit=1)

