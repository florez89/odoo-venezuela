# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged
from odoo import fields
from odoo.exceptions import UserError, ValidationError

@tagged('ve_payroll', 'post_install', '-at_install')
class TestVeSalaryRules(TransactionCase):

    def setUp(self):
        super(TestVeSalaryRules, self).setUp()
        self.company = self.env.company
        self.usd = self.env.ref('base.USD')
        self.ves = self.env.ref('base.VES', raise_if_not_found=False) or self.company.currency_id

        # Clean parameters to avoid overlaps
        self.env['l10n_ve.payroll.parameter'].search([]).unlink()

        self.param = self.env['l10n_ve.payroll.parameter'].create({
            'name': 'Parámetros Julio 2026',
            'date_start': '2026-07-01',
            'date_end': '2026-07-31',
            'salario_minimo': 130.00,
            'unidad_tributaria': 9.0,
            'cestaticket_usd': 40.0,
            'pension_rate': 9.0,
            'pension_min_base': 240.00,
            'ivss_employee_rate': 4.0,
            'ivss_employer_rate': 9.0,
            'ivss_limit_weeks': 5,
            'spf_employee_rate': 0.5,
            'spf_employer_rate': 2.0,
            'spf_limit_weeks': 10,
            'faov_employee_rate': 1.0,
            'faov_employer_rate': 2.0,
            'inces_employer_rate': 2.0,
            'inces_employee_rate': 0.5,
            'vacation_days_base': 15,
            'vacation_days_max': 30,
            'vacation_bonus_days_base': 15,
            'vacation_bonus_days_max': 30,
            'utilidades_days_min': 30,
            'utilidades_days_max': 120,
            'prestaciones_method': 'monthly',
        })

        # Setup rate for USD (36.50 VES per USD)
        self.rate_val = 1.0 / 36.50
        self.env['res.currency.rate'].search([('currency_id', '=', self.usd.id), ('name', '=', '2026-07-31')]).unlink()
        self.env['res.currency.rate'].create({
            'currency_id': self.usd.id,
            'company_id': self.company.id,
            'name': '2026-07-31',
            'rate': self.rate_val,
        })

        # Fetch salary structure
        self.structure = self.env.ref('hr_payroll.structure_002', raise_if_not_found=False)
        if not self.structure:
            self.structure = self.env['hr.payroll.structure'].search([('code', '=', 'structure_002')], limit=1) or self.env['hr.payroll.structure'].search([], limit=1)

    def _create_employee_with_contract(self, name, hire_date, wage_currency, wage_amount):
        employee = self.env['hr.employee'].create({
            'name': name,
            'wage_currency_id': wage_currency.id,
            'wage_in_currency': wage_amount,
            'contract_date_start': hire_date,
        })
        return employee, None


    def _set_input(self, payslip, code, amount):
        existing = payslip.input_line_ids.filtered(lambda l: l.code == code)
        if existing:
            existing.write({'amount': amount})
        else:
            input_type = self.env['hr.payslip.input.type'].search([('code', '=', code)], limit=1)
            if not input_type:
                input_type = self.env['hr.payslip.input.type'].create({'code': code, 'name': code})
            self.env['hr.payslip.input'].create({
                'payslip_id': payslip.id,
                'input_type_id': input_type.id,
                'code': code,
                'amount': amount,
            })

    def test_case_a_full_attendance(self):
        employee, contract = self._create_employee_with_contract(
            'Trabajador Test Reglas A', '2026-07-01', self.usd, 500.00
        )
        payslip = self.env['hr.payslip'].create({
            'name': 'Recibo Test Case A',
            'employee_id': employee.id,
            'date_from': '2026-07-01',
            'date_to': '2026-07-31',
            'struct_id': self.structure.id,
        })
        payslip.compute_sheet()
        
        # Verify Case A Cesta Ticket: $40 * 36.50 = 1460.00 VES
        ct_line = payslip.line_ids.filtered(lambda l: l.code == 'BON_ALIM')
        self.assertTrue(ct_line)
        self.assertAlmostEqual(ct_line.total, 1460.00, places=2)

    def test_case_b_proportional_attendance(self):
        employee, contract = self._create_employee_with_contract(
            'Trabajador Test Reglas B', '2026-07-01', self.usd, 500.00
        )
        payslip = self.env['hr.payslip'].create({
            'name': 'Recibo Test Case B',
            'employee_id': employee.id,
            'date_from': '2026-07-01',
            'date_to': '2026-07-31',
            'struct_id': self.structure.id,
        })
        
        # Create worked days lines: 24 worked, 6 absent (OUT)
        # Odoo 19 uses hr.payslip.worked_days
        attendance_type = self.env['hr.work.entry.type'].search([('code', '=', 'WORK100')], limit=1) or self.env['hr.work.entry.type'].search([], limit=1)
        out_type = self.env['hr.work.entry.type'].search([('code', '=', 'OUT')], limit=1) or self.env['hr.work.entry.type'].search([], limit=1)

        self.env['hr.payslip.worked_days'].create({
            'payslip_id': payslip.id,
            'work_entry_type_id': attendance_type.id,
            'code': 'WORK100',
            'number_of_days': 24.0,
            'number_of_hours': 192.0,
        })
        self.env['hr.payslip.worked_days'].create({
            'payslip_id': payslip.id,
            'work_entry_type_id': out_type.id,
            'code': 'OUT',
            'number_of_days': 6.0,
            'number_of_hours': 48.0,
        })

        payslip.compute_sheet()
        ct_line = payslip.line_ids.filtered(lambda l: l.code == 'BON_ALIM')
        self.assertTrue(ct_line)
        worked_days_sum = sum(line.number_of_days for line in payslip.worked_days_line_ids if line.code != 'OUT')
        total_planned_days = sum(line.number_of_days for line in payslip.worked_days_line_ids)
        expected_ct = 1460.00 * (worked_days_sum / total_planned_days) if total_planned_days > 0 else 1460.00
        self.assertAlmostEqual(ct_line.total, expected_ct, places=2)


    def test_case_c_profit_sharing_inces(self):
        employee, contract = self._create_employee_with_contract(
            'Trabajador Test Reglas C', '2026-07-01', self.usd, 500.00
        )
        payslip = self.env['hr.payslip'].create({
            'name': 'Recibo Test Case C (Utilidades)',
            'employee_id': employee.id,
            'date_from': '2026-07-01',
            'date_to': '2026-07-31',
            'struct_id': self.structure.id,
        })
        self._set_input(payslip, 'UTIL', 5000.00)
        payslip.compute_sheet()

        inces_ded = payslip.line_ids.filtered(lambda l: l.code == 'DED_INCES')
        self.assertTrue(inces_ded)
        self.assertAlmostEqual(inces_ded.total, -25.00, places=2)

    def test_case_d_vacations_utilities(self):
        # 1 Year Seniority
        employee_1y, contract_1y = self._create_employee_with_contract(
            'Trabajador 1 Año Antigüedad', '2025-07-01', self.usd, 500.00
        )
        payslip_1y = self.env['hr.payslip'].create({
            'name': 'Recibo Vacaciones D1',
            'employee_id': employee_1y.id,
            'date_from': '2026-07-01',
            'date_to': '2026-07-31',
            'struct_id': self.structure.id,
        })
        payslip_1y.compute_sheet()
        self.assertEqual(payslip_1y._get_vacation_days(), 15.0)
        self.assertEqual(payslip_1y._get_vacation_bonus_days(), 15.0)

        # 5 Years Seniority
        employee_5y, contract_5y = self._create_employee_with_contract(
            'Trabajador 5 Años Antigüedad', '2021-07-01', self.usd, 500.00
        )
        payslip_5y = self.env['hr.payslip'].create({
            'name': 'Recibo Vacaciones D2',
            'employee_id': employee_5y.id,
            'date_from': '2026-07-01',
            'date_to': '2026-07-31',
            'struct_id': self.structure.id,
        })
        payslip_5y.compute_sheet()
        self.assertEqual(payslip_5y._get_vacation_days(), 19.0)
        self.assertEqual(payslip_5y._get_vacation_bonus_days(), 19.0)

    def test_case_e_prestaciones_interest(self):
        self.env['l10n_ve.prestaciones.rate'].search([('date', '=', '2026-07-01')]).unlink()
        self.env['l10n_ve.prestaciones.rate'].create({
            'date': '2026-07-01',
            'rate': 36.00,
        })
        
        employee, contract = self._create_employee_with_contract(
            'Trabajador Prestaciones E', '2026-07-01', self.usd, 500.00
        )
        payslip = self.env['hr.payslip'].create({
            'name': 'Recibo Prestaciones E1',
            'employee_id': employee.id,
            'date_from': '2026-07-01',
            'date_to': '2026-07-31',
            'struct_id': self.structure.id,
        })
        payslip.compute_sheet()

        ledger = self.env['l10n_ve.prestaciones.ledger'].search([
            ('employee_id', '=', employee.id),
            ('date', '=', '2026-07-01')
        ], limit=1)
        self.assertTrue(ledger)
        self.assertEqual(ledger.state, 'draft')
        
        gar_line = payslip.line_ids.filtered(lambda l: l.code == 'GAR_PRES')
        int_line = payslip.line_ids.filtered(lambda l: l.code == 'INT_PRES')
        self.assertTrue(gar_line)
        self.assertTrue(int_line)

        payslip.action_payslip_done()
        self.assertEqual(ledger.state, 'posted')

    def test_case_g_islr(self):
        employee, contract = self._create_employee_with_contract(
            'Empleado Case G ISLR', '2026-07-01', self.usd, 500.00
        )
        
        ari = self.env['l10n_ve.ari'].create({
            'employee_id': employee.id,
            'date': '2026-07-01',
            'fiscal_year': 2026,
            'is_variation': 'initial',
            'estimated_income': 500000.00,
            'desgravamen_type': 'single',
            'carga_familiar_count': 2,
        })
        ari.action_post()
        
        self.assertAlmostEqual(ari.estimated_income_ut, 55555.56, places=1)
        self.assertAlmostEqual(ari.desgravamen_ut, 774.0)
        self.assertAlmostEqual(ari.total_rebajas_ut, 30.0)
        self.assertAlmostEqual(ari.retencion_rate, 31.90, places=1)
        
        employee.invalidate_model(['l10n_ve_ari_rate'])
        employee_ctx = employee.with_context(l10n_ve_payslip_year=2026)
        self.assertAlmostEqual(employee_ctx.l10n_ve_ari_rate, ari.retencion_rate, places=2)
        
        payslip = self.env['hr.payslip'].create({
            'name': 'Recibo Case G ISLR',
            'employee_id': employee.id,
            'date_from': '2026-07-01',
            'date_to': '2026-07-31',
            'struct_id': self.structure.id,
        })
        payslip.compute_sheet()
        islr_line = payslip.line_ids.filtered(lambda l: l.code == 'DED_ISLR')
        self.assertTrue(islr_line)
        gross_line = payslip.line_ids.filtered(lambda l: l.code == 'GROSS')
        gross_total = gross_line.total if gross_line else payslip.wage_in_ves
        expected_islr = - (gross_total * (ari.retencion_rate / 100.0))
        self.assertAlmostEqual(islr_line.total, expected_islr, places=2)

    def test_case_h_resignation_liquidation(self):
        employee, contract = self._create_employee_with_contract(
            'Empleado Resignacion', '2023-11-01', self.usd, 500.00
        )
        
        self.env['l10n_ve.prestaciones.ledger'].create({
            'employee_id': employee.id,
            'date': '2026-06-01',
            'accumulated_balance': 20000.00,
            'accumulated_interest': 1200.00,
            'state': 'posted',
        })
        
        self.env['l10n_ve.prestaciones.rate'].create({
            'date': '2026-07-01',
            'rate': 36.00,
        })
        
        wizard = self.env['l10n_ve.employee.liquidation.wizard'].create({
            'employee_id': employee.id,
            'exit_date': '2026-07-15',
            'exit_reason': 'resignation',
        })
        wizard.action_confirm()
        
        self.assertEqual(employee.l10n_ve_liquidation_state, 'to_liquidate')
        self.assertEqual(employee.l10n_ve_exit_date, fields.Date.from_string('2026-07-15'))
        self.assertEqual(employee.l10n_ve_exit_reason, 'resignation')
        
        payslip = self.env['hr.payslip'].create({
            'name': 'Recibo Liquidacion Renuncia',
            'employee_id': employee.id,
            'date_from': '2026-07-01',
            'date_to': '2026-07-15',
            'struct_id': self.structure.id,
        })
        
        completed_years, fractional_months = payslip._get_liquidation_months_and_years()
        self.assertEqual(completed_years, 2)
        self.assertEqual(fractional_months, 8)
        self.assertEqual(payslip._get_years_of_service_fraction(), 3)
        self.assertEqual(payslip._get_fractional_months(), 8)
        
        payslip.compute_sheet()
        
        liq_gar_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQ_GAR')
        liq_ret_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQ_RET')
        liq_dif_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQ_DIF')
        liq_vac_frac_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQ_VAC_FRAC')
        liq_bon_vac_frac_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQ_BON_VAC_FRAC')
        liq_util_frac_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQ_UTIL_FRAC')
        liq_ind_desp_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQ_IND_DESP')
        
        self.assertTrue(liq_gar_line)
        self.assertTrue(liq_ret_line)
        self.assertTrue(liq_dif_line)
        self.assertTrue(liq_vac_frac_line)
        self.assertTrue(liq_bon_vac_frac_line)
        self.assertTrue(liq_util_frac_line)
        self.assertFalse(liq_ind_desp_line)
        
        payslip.action_payslip_done()
        
        self.assertEqual(employee.l10n_ve_liquidation_state, 'liquidated')
        self.assertFalse(employee.active)
        
        ledger = self.env['l10n_ve.prestaciones.ledger'].search([
            ('employee_id', '=', employee.id),
            ('date', '=', '2026-07-01')
        ], limit=1)
        self.assertTrue(ledger)
        self.assertEqual(ledger.accumulated_balance, 0.0)
        self.assertEqual(ledger.accumulated_interest, 0.0)

    def test_case_i_unjustified_dismissal_liquidation(self):
        employee, contract = self._create_employee_with_contract(
            'Empleado Despido Injustificado', '2023-11-01', self.usd, 500.00
        )
        
        self.env['l10n_ve.prestaciones.ledger'].create({
            'employee_id': employee.id,
            'date': '2026-06-01',
            'accumulated_balance': 20000.00,
            'accumulated_interest': 1200.00,
            'state': 'posted',
        })
        
        self.env['l10n_ve.prestaciones.rate'].create({
            'date': '2026-07-01',
            'rate': 36.00,
        })
        
        wizard = self.env['l10n_ve.employee.liquidation.wizard'].create({
            'employee_id': employee.id,
            'exit_date': '2026-07-15',
            'exit_reason': 'unjustified_dismissal',
        })
        wizard.action_confirm()
        
        payslip = self.env['hr.payslip'].create({
            'name': 'Recibo Liquidacion Despido',
            'employee_id': employee.id,
            'date_from': '2026-07-01',
            'date_to': '2026-07-15',
            'struct_id': self.structure.id,
        })
        payslip.compute_sheet()
        
        liq_gar_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQ_GAR')
        liq_dif_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQ_DIF')
        liq_ind_desp_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQ_IND_DESP')
        
        self.assertTrue(liq_ind_desp_line)
        expected_ind = (liq_gar_line.total if liq_gar_line else 0.0) + (liq_dif_line.total if liq_dif_line else 0.0)
        self.assertAlmostEqual(liq_ind_desp_line.total, expected_ind, places=2)
