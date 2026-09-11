# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

class DestajoSemanal(models.Model):
    _name = 'destajo.semanal'
    _description = 'Planilla Semanal de Producción y Liquidación'
    _order = 'date_to desc, id desc'

    name = fields.Char(string='Descripción / Período', required=True, default='Semana Nueva')
    date_from = fields.Date(string='Desde', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='Hasta', required=True, default=fields.Date.context_today)
    
    bcv_rate = fields.Float(
        string='Tasa Oficial BCV (VES/$)', 
        compute='_compute_bcv_rate', 
        store=True, 
        readonly=False, 
        digits=(16, 4),
        help='Tasa BCV oficial a aplicar para convertir los dólares producidos a Bolívares.'
    )
    
    state = fields.Selection([
        ('draft', 'Carga en Taller'),
        ('computed', 'Resumen Calculado'),
        ('transferred', 'Transferido a Nómina')
    ], string='Estado', default='draft', required=True, copy=False)

    line_ids = fields.One2many('destajo.line', 'semanal_id', string='Registro de Tareas / Piezas')
    resumen_ids = fields.One2many('destajo.resumen.line', 'semanal_id', string='Resumen de Liquidación')

    total_piezas = fields.Integer(string='Total Piezas Elaboradas', compute='_compute_totales_semanal', store=True)
    total_destajo_usd = fields.Float(string='Total Destajo ($ USD)', compute='_compute_totales_semanal', store=True, digits=(16, 2))
    total_devengado_usd = fields.Float(string='Gran Total Devengado ($ USD)', compute='_compute_totales_semanal', store=True, digits=(16, 2))
    total_devengado_ves = fields.Float(string='Gran Total en Bolívares (VES)', compute='_compute_totales_semanal', store=True, digits=(16, 2))
    
    payslip_count = fields.Integer(string='N° Recibos de Nómina', compute='_compute_payslip_count')

    @api.depends('date_to')
    def _compute_bcv_rate(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for rec in self:
            if not usd:
                rec.bcv_rate = 1.0
                continue
            company = self.env.company
            date = rec.date_to or fields.Date.context_today(self)
            try:
                rate = usd._convert(1.0, company.currency_id, company, date)
                rec.bcv_rate = rate or 1.0
            except Exception:
                rec.bcv_rate = 1.0

    @api.depends('line_ids', 'line_ids.qty', 'line_ids.total_usd', 'resumen_ids', 'resumen_ids.total_usd', 'resumen_ids.total_ves')
    def _compute_totales_semanal(self):
        for rec in self:
            rec.total_piezas = sum(line.qty for line in rec.line_ids)
            rec.total_destajo_usd = sum(line.total_usd for line in rec.line_ids)
            if rec.resumen_ids:
                rec.total_devengado_usd = sum(res.total_usd for res in rec.resumen_ids)
                rec.total_devengado_ves = sum(res.total_ves for res in rec.resumen_ids)
            else:
                rec.total_devengado_usd = rec.total_destajo_usd
                rec.total_devengado_ves = rec.total_destajo_usd * (rec.bcv_rate or 1.0)

    def _compute_payslip_count(self):
        for rec in self:
            rec.payslip_count = len(rec.resumen_ids.mapped('payslip_id'))

    def action_calcular_resumen(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError("Debe registrar al menos una línea de piezas en la semana antes de calcular el resumen.")
        
        # Eliminar resumen previo
        self.resumen_ids.unlink()
        
        # Agrupar por empleado
        emp_totals = {}
        for line in self.line_ids:
            if not line.employee_id:
                continue
            emp_id = line.employee_id.id
            emp_totals[emp_id] = emp_totals.get(emp_id, 0.0) + line.total_usd

        resumen_vals = []
        for emp_id, destajo_usd in emp_totals.items():
            emp = self.env['hr.employee'].browse(emp_id)
            
            # Obtener sueldo fijo pactado en contrato (si aplica)
            wage_fixed = 0.0
            if hasattr(emp, 'wage_currency_id') and emp.wage_currency_id and emp.wage_currency_id.name == 'USD':
                wage_fixed = emp.wage_in_currency
            elif hasattr(emp, 'wage'):
                wage_fixed = emp.wage / (self.bcv_rate or 1.0) if self.bcv_rate > 0 else 0.0

            total_usd = wage_fixed + destajo_usd
            total_ves = total_usd * (self.bcv_rate or 1.0)

            resumen_vals.append({
                'semanal_id': self.id,
                'employee_id': emp.id,
                'wage_fixed_usd': wage_fixed,
                'destajo_usd': destajo_usd,
                'total_usd': total_usd,
                'bcv_rate': self.bcv_rate,
                'total_ves': total_ves,
            })

        self.env['destajo.resumen.line'].create(resumen_vals)
        self.state = 'computed'

    def action_pasar_a_nomina(self):
        self.ensure_one()
        if not self.resumen_ids:
            self.action_calcular_resumen()

        input_type = self.env['hr.payslip.input.type'].search([('code', '=', 'PRODUCCION')], limit=1)
        if not input_type:
            input_type = self.env['hr.payslip.input.type'].create({
                'name': 'Pago por Producción / Destajo (USD)',
                'code': 'PRODUCCION',
                'active': True,
            })

        payslip_obj = self.env['hr.payslip']
        for resumen in self.resumen_ids:
            emp = resumen.employee_id
            
            # Buscar o crear recibo de nómina del empleado para este período
            payslip = payslip_obj.search([
                ('employee_id', '=', emp.id),
                ('date_from', '=', self.date_from),
                ('date_to', '=', self.date_to),
                ('state', 'in', ['draft', 'verify'])
            ], limit=1)

            if not payslip:
                payslip = payslip_obj.create({
                    'name': f"Nómina Semanal - {emp.name} ({self.name})",
                    'employee_id': emp.id,
                    'date_from': self.date_from,
                    'date_to': self.date_to,
                })

            # Forzar tasa BCV si aplica
            if hasattr(payslip, 'l10n_ve_bcv_rate') and self.bcv_rate > 0:
                payslip.l10n_ve_bcv_rate = self.bcv_rate

            # Crear o actualizar línea de Otras Entradas (PRODUCCION)
            input_line = payslip.input_line_ids.filtered(lambda l: l.input_type_id.id == input_type.id or l.code == 'PRODUCCION')
            if input_line:
                input_line.write({'amount': resumen.destajo_usd})
            else:
                self.env['hr.payslip.input'].create({
                    'payslip_id': payslip.id,
                    'input_type_id': input_type.id,
                    'amount': resumen.destajo_usd,
                })

            # Recalcular la hoja de salario
            payslip.compute_sheet()
            resumen.payslip_id = payslip.id

        self.state = 'transferred'

    def action_ver_recibos(self):
        self.ensure_one()
        payslip_ids = self.resumen_ids.mapped('payslip_id').ids
        return {
            'name': 'Recibos de Nómina Generados',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('id', 'in', payslip_ids)],
            'target': 'current',
        }


class DestajoLine(models.Model):
    _name = 'destajo.line'
    _description = 'Línea de Producción por Trabajador'
    _order = 'employee_id, lote_id, operacion_id'

    semanal_id = fields.Many2one('destajo.semanal', string='Planilla Semanal', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', string='Trabajador / Costurera', required=True, index=True)
    lote_id = fields.Many2one('destajo.lote', string='Lote / Corte', required=True, index=True)
    producto_id = fields.Many2one('destajo.producto', string='Producto / Prenda', related='lote_id.producto_id', store=True, readonly=True)
    operacion_id = fields.Many2one('destajo.operacion', string='Operación / Tarea', required=True, index=True)
    
    qty = fields.Integer(string='Cant. Piezas', required=True, default=1)
    price_usd = fields.Float(string='Tarifa Unit. ($ USD)', required=True, default=0.0, digits=(16, 4))
    total_usd = fields.Float(string='Total ($ USD)', compute='_compute_total_usd', store=True, digits=(16, 2))

    @api.onchange('lote_id')
    def _onchange_lote_id(self):
        self.operacion_id = False
        if self.lote_id:
            return {'domain': {'operacion_id': [('producto_id', '=', self.lote_id.producto_id.id)]}}
        return {'domain': {'operacion_id': []}}

    @api.onchange('operacion_id')
    def _onchange_operacion_id(self):
        if self.operacion_id:
            self.price_usd = self.operacion_id.price_usd

    @api.depends('qty', 'price_usd')
    def _compute_total_usd(self):
        for line in self:
            line.total_usd = line.qty * line.price_usd


class DestajoResumenLine(models.Model):
    _name = 'destajo.resumen.line'
    _description = 'Resumen de Liquidación Semanal por Empleado'
    _order = 'employee_id'

    semanal_id = fields.Many2one('destajo.semanal', string='Planilla Semanal', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', string='Trabajador', required=True, index=True)
    job_title = fields.Char(string='Cargo / Función', related='employee_id.job_title')
    
    wage_fixed_usd = fields.Float(string='Sueldo Fijo ($ USD)', default=0.0, digits=(16, 2),
                                  help='Sueldo base pactado en el contrato del empleado.')
    destajo_usd = fields.Float(string='Total Destajo ($ USD)', default=0.0, digits=(16, 2),
                               help='Total acumulado por piezas elaboradas en la semana.')
    total_usd = fields.Float(string='Total Devengado ($ USD)', default=0.0, digits=(16, 2),
                             help='Suma del Sueldo Fijo + Destajo en Dólares.')
    bcv_rate = fields.Float(string='Tasa BCV', digits=(16, 4))
    total_ves = fields.Float(string='Total en Bolívares (VES)', digits=(16, 2),
                             help='Total a pagar convertido a Bolívares a la tasa BCV.')

    payslip_id = fields.Many2one('hr.payslip', string='Recibo de Nómina', readonly=True)
