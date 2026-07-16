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
        amount = input_line[0].amount if input_line else 0.0
        if amount == 0.0:
            param = self._get_active_ve_parameter()
            if not param:
                return 0.0
            seniority = self._get_lottt_seniority_years()
            if seniority < 1:
                return 0.0
            calculated_days = param.vacation_days_base + (seniority - 1)
            return min(calculated_days, param.vacation_days_max)
        return amount

    def _get_vacation_bonus_days(self):
        self.ensure_one()
        input_line = self.input_line_ids.filtered(lambda l: l.code == 'BON_VAC_DAYS')
        amount = input_line[0].amount if input_line else 0.0
        if amount == 0.0:
            param = self._get_active_ve_parameter()
            if not param:
                return 0.0
            seniority = self._get_lottt_seniority_years()
            if seniority < 1:
                return 0.0
            calculated_days = param.vacation_bonus_days_base + (seniority - 1)
            return min(calculated_days, param.vacation_bonus_days_max)
        return amount

    def _get_utilidades_days(self):
        self.ensure_one()
        input_line = self.input_line_ids.filtered(lambda l: l.code == 'UTIL_DAYS')
        amount = input_line[0].amount if input_line else 0.0
        if amount == 0.0:
            param = self._get_active_ve_parameter()
            if not param:
                return 0.0
            return float(param.utilidades_days_min)
        return amount

    def _get_ve_salary_integral_daily(self):
        self.ensure_one()
        daily_wage = self.wage_in_ves / 30.0
        param = self._get_active_ve_parameter()
        if not param:
            return daily_wage
        seniority = self._get_lottt_seniority_years()
        if seniority >= 1:
            vac_days = param.vacation_bonus_days_base + (seniority - 1)
            vac_days = min(vac_days, param.vacation_bonus_days_max)
        else:
            vac_days = param.vacation_bonus_days_base
        
        util_days = param.utilidades_days_min
        
        aliquot_vac = (daily_wage * vac_days) / 360.0
        aliquot_util = (daily_wage * util_days) / 360.0
        return daily_wage + aliquot_vac + aliquot_util

    def _is_quarterly_anniversary(self):
        self.ensure_one()
        start_date = self.employee_id.contract_date_start
        if not start_date or not self.date_to:
            return False
        months_tenure = (self.date_to.year - start_date.year) * 12 + (self.date_to.month - start_date.month) + 1
        return months_tenure > 0 and months_tenure % 3 == 0

    def _get_ve_prestaciones_adicionales_days(self):
        self.ensure_one()
        start_date = self.employee_id.contract_date_start
        if not start_date or not self.date_to:
            return 0.0
        if self.date_to.month != start_date.month:
            return 0.0
        seniority = self._get_lottt_seniority_years()
        if seniority < 2:
            return 0.0
        return min(2 * (seniority - 1), 30.0)

    def _update_ve_prestaciones_ledger(self, state='draft'):
        for slip in self:
            if not slip.employee_id or not slip.date_to:
                continue
            
            month_start = slip.date_to.replace(day=1)
            param = slip._get_active_ve_parameter()
            if not param:
                continue
                
            if param.prestaciones_method == 'monthly':
                days_gar = 5.0
            else:
                days_gar = 15.0 if slip._is_quarterly_anniversary() else 0.0
                
            days_adic = slip._get_ve_prestaciones_adicionales_days()
            
            daily_integral = slip._get_ve_salary_integral_daily()
            amount_gar = days_gar * daily_integral
            amount_adic = days_adic * (slip.wage_in_ves / 30.0)
            
            prev_ledger = self.env['l10n_ve.prestaciones.ledger'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('date', '<', month_start),
                ('state', '=', 'posted')
            ], order='date desc', limit=1)
            
            prev_balance = prev_ledger.accumulated_balance if prev_ledger else 0.0
            prev_accum_interest = prev_ledger.accumulated_interest if prev_ledger else 0.0
            
            rate_rec = self.env['l10n_ve.prestaciones.rate'].search([
                ('date', '<=', month_start)
            ], order='date desc', limit=1)
            interest_rate = rate_rec.rate if rate_rec else 0.0
            
            accumulated_balance = prev_balance + amount_gar + amount_adic
            amount_interest = accumulated_balance * (interest_rate / 100.0) / 12.0
            accumulated_interest = prev_accum_interest + amount_interest
            
            ledger = self.env['l10n_ve.prestaciones.ledger'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('date', '=', month_start)
            ], limit=1)
            
            vals = {
                'employee_id': slip.employee_id.id,
                'payslip_id': slip.id,
                'date': month_start,
                'salary_integral_daily': daily_integral,
                'days_garantia': days_gar,
                'amount_garantia': amount_gar,
                'days_adicionales': days_adic,
                'amount_adicionales': amount_adic,
                'previous_balance': prev_balance,
                'accumulated_balance': accumulated_balance,
                'bcv_rate_id': rate_rec.id if rate_rec else False,
                'bcv_interest_rate': interest_rate,
                'amount_interest': amount_interest,
                'previous_accumulated_interest': prev_accum_interest,
                'accumulated_interest': accumulated_interest,
                'state': state
            }
            
            if ledger:
                if ledger.state == 'draft' or state == 'posted':
                    ledger.write(vals)
            else:
                self.env['l10n_ve.prestaciones.ledger'].create(vals)

    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()
        self._update_ve_prestaciones_ledger(state='posted')
        return res

    def action_payslip_cancel(self):
        res = super(HrPayslip, self).action_payslip_cancel()
        for slip in self:
            ledger = self.env['l10n_ve.prestaciones.ledger'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('date', '=', slip.date_to.replace(day=1))
            ])
            if ledger:
                ledger.write({'state': 'draft'})
        return res

    def compute_sheet(self):
        res = super(HrPayslip, self).compute_sheet()
        self._update_ve_prestaciones_ledger(state='draft')
        return res

