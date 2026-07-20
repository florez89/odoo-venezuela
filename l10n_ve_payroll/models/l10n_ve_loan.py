# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class L10nVeLoan(models.Model):
    _name = 'l10n_ve.loan'
    _description = 'Préstamos a Trabajadores Venezuela'
    _order = 'date desc, id desc'

    name = fields.Char(string='Referencia de Préstamo', required=True, default='/', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, index=True)
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True, default=lambda self: self.env.company.currency_id)
    
    date = fields.Date(string='Fecha de Solicitud', required=True, default=fields.Date.context_today)
    amount = fields.Monetary(string='Monto Total del Préstamo', required=True, currency_field='currency_id')
    installments = fields.Integer(string='Número de Cuotas', required=True, default=1)
    installment_amount = fields.Monetary(string='Monto por Cuota', compute='_compute_installment_amount', store=True, currency_field='currency_id')
    
    paid_amount = fields.Monetary(string='Monto Pagado', compute='_compute_loan_amounts', store=True, currency_field='currency_id')
    balance_amount = fields.Monetary(string='Saldo Pendiente', compute='_compute_loan_amounts', store=True, currency_field='currency_id')
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('approved', 'Aprobado'),
        ('paid', 'Totalmente Pagado'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='draft', required=True, tracking=True)

    line_ids = fields.One2many('l10n_ve.loan.line', 'loan_id', string='Cuotas del Préstamo')
    notes = fields.Text(string='Observaciones / Motivo')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('l10n_ve.loan') or _('PR/NEW')
        return super(L10nVeLoan, self).create(vals_list)

    @api.depends('amount', 'installments')
    def _compute_installment_amount(self):
        for record in self:
            if record.installments > 0:
                record.installment_amount = round(record.amount / record.installments, 2)
            else:
                record.installment_amount = 0.0

    @api.depends('line_ids.paid', 'line_ids.amount', 'amount')
    def _compute_loan_amounts(self):
        for record in self:
            paid_sum = sum(line.amount for line in record.line_ids if line.paid)
            record.paid_amount = paid_sum
            record.balance_amount = max(0.0, record.amount - paid_sum)
            if record.state == 'approved' and record.balance_amount <= 0.001 and len(record.line_ids) > 0:
                record.state = 'paid'

    def action_approve(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("El monto del préstamo debe ser mayor a cero."))
            if record.installments <= 0:
                raise ValidationError(_("El número de cuotas debe ser al menos 1."))
            
            # Remove old draft lines
            record.line_ids.unlink()
            
            # Generate loan installment lines
            lines = []
            per_line = record.installment_amount
            for i in range(record.installments):
                # Adjust last installment for rounding differences
                if i == record.installments - 1:
                    line_amount = round(record.amount - (per_line * (record.installments - 1)), 2)
                else:
                    line_amount = per_line
                
                lines.append((0, 0, {
                    'loan_id': record.id,
                    'sequence': i + 1,
                    'amount': line_amount,
                    'paid': False,
                }))
            record.write({
                'line_ids': lines,
                'state': 'approved'
            })

    def action_cancel(self):
        for record in self:
            if any(line.paid for line in record.line_ids):
                raise ValidationError(_("No se puede cancelar un préstamo que ya tiene cuotas pagadas."))
            record.state = 'cancelled'

    def action_draft(self):
        for record in self:
            record.state = 'draft'


class L10nVeLoanLine(models.Model):
    _name = 'l10n_ve.loan.line'
    _description = 'Cuota de Préstamo a Trabajador'
    _order = 'sequence, id'

    loan_id = fields.Many2one('l10n_ve.loan', string='Préstamo', required=True, ondelete='cascade')
    sequence = fields.Integer(string='N° Cuota', default=1)
    employee_id = fields.Many2one('hr.employee', related='loan_id.employee_id', store=True, string='Empleado')
    currency_id = fields.Many2one('res.currency', related='loan_id.currency_id', store=True)
    
    amount = fields.Monetary(string='Monto de la Cuota', required=True, currency_field='currency_id')
    paid = fields.Boolean(string='Pagada', default=False)
    payslip_id = fields.Many2one('hr.payslip', string='Recibo de Nómina', ondelete='set null')
