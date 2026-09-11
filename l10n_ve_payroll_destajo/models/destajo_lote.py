# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class DestajoLote(models.Model):
    _name = 'destajo.lote'
    _description = 'Lote de Producción / Corte de Tela'
    _order = 'date desc, id desc'

    name = fields.Char(string='Código / N° de Corte o Lote', required=True, copy=False, index=True)
    producto_id = fields.Many2one('destajo.producto', string='Producto / Prenda', required=True, index=True)
    date = fields.Date(string='Fecha de Corte / Inicio', default=fields.Date.context_today, required=True)
    total_piezas = fields.Integer(string='Total Piezas Programadas / Cortadas', required=True, default=0)
    
    cortador_id = fields.Many2one('hr.employee', string='Cortador Asignado')
    encargado_id = fields.Many2one('hr.employee', string='Encargado / Supervisor')
    notes = fields.Text(string='Observaciones')

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('in_progress', 'En Producción'),
        ('done', 'Finalizado'),
        ('cancel', 'Cancelado')
    ], string='Estado', default='draft', required=True, copy=False)

    line_ids = fields.One2many('destajo.line', 'lote_id', string='Detalle de Piezas Registradas')
    
    total_piezas_registradas = fields.Integer(string='Piezas Registradas (Máx)', compute='_compute_avance', store=True)
    porcentaje_avance = fields.Float(string='% Avance', compute='_compute_avance', store=True, digits=(16, 2))
    costo_total_acumulado_usd = fields.Float(string='Total Devengado Lote ($ USD)', compute='_compute_avance', store=True, digits=(16, 2))

    @api.depends('line_ids', 'line_ids.qty', 'line_ids.total_usd', 'total_piezas')
    def _compute_avance(self):
        for lote in self:
            if not lote.line_ids:
                lote.total_piezas_registradas = 0
                lote.porcentaje_avance = 0.0
                lote.costo_total_acumulado_usd = 0.0
                continue
            op_sums = {}
            for line in lote.line_ids:
                op_sums[line.operacion_id.id] = op_sums.get(line.operacion_id.id, 0) + line.qty
            max_qty = max(op_sums.values()) if op_sums else 0
            lote.total_piezas_registradas = max_qty
            lote.costo_total_acumulado_usd = sum(line.total_usd for line in lote.line_ids)
            lote.porcentaje_avance = (max_qty / lote.total_piezas * 100.0) if lote.total_piezas > 0 else 0.0

    def action_start(self):
        for rec in self:
            if rec.total_piezas <= 0:
                raise ValidationError("El total de piezas cortadas/programadas debe ser mayor a 0.")
            rec.state = 'in_progress'

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
