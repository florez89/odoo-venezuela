# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class L10nVeAri(models.Model):
    _name = 'l10n_ve.ari'
    _description = 'Formulario AR-I de Estimación de ISLR'
    _order = 'fiscal_year desc, date desc'

    name = fields.Char(string='Nombre', compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, ondelete='cascade')
    date = fields.Date(string='Fecha de Presentación', required=True, default=fields.Date.context_today)
    fiscal_year = fields.Integer(string='Año Gravable', required=True, default=lambda self: fields.Date.context_today(self).year)
    is_variation = fields.Selection([
        ('initial', 'Inicial'),
        ('march', 'Marzo'),
        ('june', 'Junio'),
        ('september', 'Septiembre'),
        ('december', 'Diciembre')
    ], string='Variación', default='initial', required=True)
    
    estimated_income = fields.Float(string='Remuneraciones Estimadas (VES)', digits=(16, 2), required=True, default=0.0)
    estimated_income_ut = fields.Float(string='Remuneraciones Estimadas (U.T.)', compute='_compute_ari_values', store=True, digits=(16, 2))
    
    desgravamen_type = fields.Selection([
        ('single', 'Único (774 U.T.)'),
        ('detailed', 'Detallado')
    ], string='Tipo Desgravamen', default='single', required=True)
    desgravamen_detailed = fields.Float(string='Desgravámenes Detallados (VES)', digits=(16, 2), default=0.0)
    desgravamen_ut = fields.Float(string='Desgravamen (U.T.)', compute='_compute_ari_values', store=True, digits=(16, 2))
    
    carga_familiar_count = fields.Integer(string='Cargas Familiares', default=0)
    carga_familiar_ut = fields.Float(string='Rebaja Familiar (U.T.)', compute='_compute_ari_values', store=True, digits=(16, 2))
    rebaja_personal_ut = fields.Float(string='Rebaja Personal (U.T.)', compute='_compute_ari_values', store=True, digits=(16, 2), default=10.0)
    taxes_retained_excess_ut = fields.Float(string='Retención Exceso Año Anterior (U.T.)', digits=(16, 2), default=0.0)
    
    total_rebajas_ut = fields.Float(string='Total Rebajas (U.T.)', compute='_compute_ari_values', store=True, digits=(16, 2))
    estimated_tax_ut = fields.Float(string='Impuesto Estimado (U.T.)', compute='_compute_ari_values', store=True, digits=(16, 2))
    estimated_tax_to_retain_ut = fields.Float(string='Impuesto a Retener (U.T.)', compute='_compute_ari_values', store=True, digits=(16, 2))
    retencion_rate = fields.Float(string='Porcentaje de Retención (%)', compute='_compute_ari_values', store=True, digits=(16, 2))
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Validado')
    ], string='Estado', default='draft', required=True)

    @api.depends('employee_id', 'fiscal_year')
    def _compute_name(self):
        for rec in self:
            if rec.employee_id and rec.fiscal_year:
                rec.name = f"AR-I {rec.fiscal_year} - {rec.employee_id.name}"
            else:
                rec.name = "AR-I"

    @api.depends('date', 'estimated_income', 'desgravamen_detailed', 'desgravamen_type', 'carga_familiar_count', 'taxes_retained_excess_ut')
    def _compute_ari_values(self):
        for rec in self:
            date_ref = rec.date or fields.Date.context_today(self)
            param = self.env['l10n_ve.payroll.parameter'].get_active_parameters(date_ref, self.env.company.id)
            ut_value = param.unidad_tributaria if param else 9.0
            
            # Estimated income in UT
            rec.estimated_income_ut = rec.estimated_income / ut_value if ut_value else 0.0
            
            # Desgravamen in UT
            if rec.desgravamen_type == 'single':
                rec.desgravamen_ut = 774.0
            else:
                rec.desgravamen_ut = rec.desgravamen_detailed / ut_value if ut_value else 0.0
                
            # Cargas familiares: 10 UT per load
            rec.carga_familiar_ut = rec.carga_familiar_count * 10.0
            # Rebaja personal: 10 UT by law
            rec.rebaja_personal_ut = 10.0
            
            # Total rebajas
            rec.total_rebajas_ut = rec.carga_familiar_ut + 10.0 + rec.taxes_retained_excess_ut
            
            # Taxable base: estimated income UT - desgravamen UT
            taxable_base_ut = max(0.0, rec.estimated_income_ut - rec.desgravamen_ut)
            
            # Tarifa 1 calculation
            base = taxable_base_ut
            if base <= 1000.0:
                tax = base * 0.06 - 0.0
            elif base <= 1500.0:
                tax = base * 0.09 - 30.0
            elif base <= 2000.0:
                tax = base * 0.12 - 75.0
            elif base <= 2500.0:
                tax = base * 0.16 - 155.0
            elif base <= 3000.0:
                tax = base * 0.20 - 255.0
            elif base <= 4000.0:
                tax = base * 0.24 - 375.0
            elif base <= 6000.0:
                tax = base * 0.29 - 575.0
            else:
                tax = base * 0.34 - 875.0
                
            rec.estimated_tax_ut = max(0.0, tax)
            rec.estimated_tax_to_retain_ut = max(0.0, rec.estimated_tax_ut - rec.total_rebajas_ut)
            
            if rec.estimated_income_ut > 0.0:
                rec.retencion_rate = (rec.estimated_tax_to_retain_ut / rec.estimated_income_ut) * 100.0
            else:
                rec.retencion_rate = 0.0

    def action_post(self):
        self.write({'state': 'posted'})

    def action_draft(self):
        self.write({'state': 'draft'})
