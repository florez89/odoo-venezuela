# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class L10nVePayrollParameter(models.Model):
    _name = 'l10n_ve.payroll.parameter'
    _description = 'Parámetros de Nómina Venezuela'
    _order = 'date_start desc'

    name = fields.Char(string='Descripción', required=True, copy=False)
    company_id = fields.Many2one(
        'res.company', 
        string='Compañía', 
        required=True, 
        default=lambda self: self.env.company
    )
    date_start = fields.Date(string='Fecha Inicio', required=True)
    date_end = fields.Date(string='Fecha Fin', required=True)

    # Constantes y salarios
    salario_minimo = fields.Float(string='Salario Mínimo Legal (VES)', default=130.0, required=True)
    unidad_tributaria = fields.Float(string='Unidad Tributaria (UT VES)', default=9.0, required=True)
    cestaticket_usd = fields.Float(string='Cesta Ticket Base (USD)', default=40.0, required=True)

    # Ley de Protección de Pensiones 2024
    pension_rate = fields.Float(string='Alícuota Pensiones 2024 (Patronal %)', default=9.0, required=True)
    pension_min_base = fields.Float(string='Piso Mínimo Pensiones (Ingreso Indexado USD)', default=240.0, required=True)

    # IVSS (Seguro Social)
    ivss_employee_rate = fields.Float(string='IVSS Retención Empleado (%)', default=4.0, required=True)
    ivss_employer_rate = fields.Float(string='IVSS Aporte Patronal (%)', default=9.0, required=True,
        help="9% riesgo mínimo, 10% riesgo medio, 11% riesgo máximo")
    ivss_limit_weeks = fields.Integer(string='Tope IVSS (Salarios Mínimos)', default=5, required=True)

    # SPF (Paro Forzoso)
    spf_employee_rate = fields.Float(string='SPF Retención Empleado (%)', default=0.5, required=True)
    spf_employer_rate = fields.Float(string='SPF Aporte Patronal (%)', default=2.0, required=True)
    spf_limit_weeks = fields.Integer(string='Tope SPF (Salarios Mínimos)', default=10, required=True)

    # FAOV / LPH (Aporte de Vivienda)
    faov_employee_rate = fields.Float(string='FAOV Retención Empleado (%)', default=1.0, required=True)
    faov_employer_rate = fields.Float(string='FAOV Aporte Patronal (%)', default=2.0, required=True)

    # INCES
    inces_employer_rate = fields.Float(string='INCES Aporte Patronal (%)', default=2.0, required=True)
    inces_employee_rate = fields.Float(string='INCES Retención Empleado (Utilidades %)', default=0.5, required=True)

    # Vacaciones
    vacation_days_base = fields.Integer(string='Días de Vacaciones Base', default=15, required=True)
    vacation_days_max = fields.Integer(string='Días de Vacaciones Máximo', default=30, required=True)
    vacation_bonus_days_base = fields.Integer(string='Días Bono Vacacional Base', default=15, required=True)
    vacation_bonus_days_max = fields.Integer(string='Días Bono Vacacional Máximo', default=30, required=True)

    # Utilidades
    utilidades_days_min = fields.Integer(string='Días de Utilidades Mínimo', default=30, required=True)
    utilidades_days_max = fields.Integer(string='Días de Utilidades Máximo', default=120, required=True)

    @api.constrains('date_start', 'date_end', 'company_id')
    def _check_date_overlaps(self):
        for rec in self:
            if rec.date_start > rec.date_end:
                raise ValidationError(_("La fecha de inicio no puede ser posterior a la fecha de fin."))

            # Buscar otros registros de parámetros de la misma compañía que se solapen
            overlapping = self.search([
                ('id', '!=', rec.id),
                ('company_id', '=', rec.company_id.id),
                ('date_start', '<=', rec.date_end),
                ('date_end', '>=', rec.date_start),
            ])
            if overlapping:
                raise ValidationError(_(
                    "Los parámetros de nómina se solapan con el registro '%s' (%s a %s)."
                ) % (overlapping[0].name, overlapping[0].date_start, overlapping[0].date_end))

    @api.model
    def get_active_parameters(self, date_target, company_id=None):
        if not company_id:
            company_id = self.env.company.id
        # Primero buscar coincidencia exacta
        res = self.search([
            ('company_id', '=', company_id),
            ('date_start', '<=', date_target),
            ('date_end', '>=', date_target)
        ], limit=1)
        if not res:
            # Si no hay, retornar el último registro disponible
            res = self.search([
                ('company_id', '=', company_id)
            ], order='date_start desc', limit=1)
        return res
