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

    def _get_cestaticket_amount(self):
        self.ensure_one()
        param = self._get_active_ve_parameter()
        if not param:
            return 0.0
        
        # Base amount (USD converted to company currency using the BCV rate)
        base_amount = param.cestaticket_usd * self.l10n_ve_bcv_rate
        
        if not self.worked_days_line_ids:
            return base_amount
            
        # Sum of days worked/paid (excluding unpaid leaves like OUT)
        worked_days_sum = sum(line.number_of_days for line in self.worked_days_line_ids if line.code != 'OUT')
        total_planned_days = sum(line.number_of_days for line in self.worked_days_line_ids)
        
        if total_planned_days <= 0:
            return base_amount
            
        proportion = min(worked_days_sum / total_planned_days, 1.0)
        return base_amount * proportion

    def _get_lottt_seniority_years(self):
        self.ensure_one()
        start_date = self.employee_id.contract_date_start
        if not start_date:
            return 0

        date_target = self.date_to or fields.Date.context_today(self)
        if start_date > date_target:
            return 0
        delta = date_target - start_date
        return delta.days // 365

    def _get_vacation_days(self):
        self.ensure_one()
        input_line = self.input_line_ids.filtered(lambda l: l.code == 'VAC_DAYS')
        if not input_line:
            return 0.0

        if input_line[0].amount == 0.0:
            param = self._get_active_ve_parameter()
            if not param:
                return 0.0
            seniority = self._get_lottt_seniority_years()
            if seniority < 1:
                return 0.0
            calculated_days = param.vacation_days_base + (seniority - 1)
            return min(calculated_days, param.vacation_days_max)

        return input_line[0].amount

    def _get_vacation_bonus_days(self):
        self.ensure_one()
        input_line = self.input_line_ids.filtered(lambda l: l.code == 'BON_VAC_DAYS')
        if not input_line:
            return 0.0

        if input_line[0].amount == 0.0:
            param = self._get_active_ve_parameter()
            if not param:
                return 0.0
            seniority = self._get_lottt_seniority_years()
            if seniority < 1:
                return 0.0
            calculated_days = param.vacation_bonus_days_base + (seniority - 1)
            return min(calculated_days, param.vacation_bonus_days_max)

        return input_line[0].amount

    def _get_utilidades_days(self):
        self.ensure_one()
        input_line = self.input_line_ids.filtered(lambda l: l.code == 'UTIL_DAYS')
        if not input_line:
            return 0.0

        if input_line[0].amount == 0.0:
            param = self._get_active_ve_parameter()
            if not param:
                return 0.0
            return float(param.utilidades_days_min)

        return input_line[0].amount
