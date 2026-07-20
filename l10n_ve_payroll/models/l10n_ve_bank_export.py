# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class L10nVePayrollBankExportWizard(models.TransientModel):
    _name = 'l10n_ve.payroll.bank.export.wizard'
    _description = 'Asistente de Exportación de TXT Bancarios para Nómina'

    bank_id = fields.Selection([
        ('bdv', 'Banco de Venezuela (BDV)'),
        ('banesco', 'Banesco Banco Universal'),
        ('mercantil', 'Banco Mercantil'),
        ('provincial', 'BBVA Banco Provincial'),
    ], string='Banco Emisor / Formato', required=True, default='bdv')

    date_from = fields.Date(string='Desde', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='Hasta', required=True, default=fields.Date.context_today)
    company_bank_account = fields.Char(string='Número de Cuenta Origen (Empresa)', required=True, help='Cuenta bancaria de 20 dígitos de la empresa emisora')
    
    payslip_ids = fields.Many2many('hr.payslip', string='Recibos de Nómina Incluidos')
    
    file_data = fields.Binary(string='Archivo TXT Generado', readonly=True)
    file_name = fields.Char(string='Nombre del Archivo', readonly=True)

    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        if self.date_from and self.date_to:
            slips = self.env['hr.payslip'].search([
                ('date_from', '>=', self.date_from),
                ('date_to', '<=', self.date_to),
                ('state', 'in', ['done', 'paid', 'verify', 'draft']),
            ])
            self.payslip_ids = slips

    def action_generate_txt(self):
        self.ensure_one()
        if not self.payslip_ids:
            raise UserError(_("Debe seleccionar al menos un recibo de nómina para generar el archivo bancario."))
        
        # Ensure account string format
        clean_company_account = (self.company_bank_account or '').replace('-', '').replace(' ', '').zfill(20)
        
        lines = []
        if self.bank_id == 'bdv':
            lines = self._generate_bdv_txt(clean_company_account)
        elif self.bank_id == 'banesco':
            lines = self._generate_banesco_txt(clean_company_account)
        elif self.bank_id == 'mercantil':
            lines = self._generate_mercantil_txt(clean_company_account)
        elif self.bank_id == 'provincial':
            lines = self._generate_provincial_txt(clean_company_account)
            
        txt_content = "\r\n".join(lines)
        encoded_data = base64.b64encode(txt_content.encode('latin1', errors='replace'))
        
        filename = f"nomina_{self.bank_id}_{fields.Date.today().strftime('%Y%m%d')}.txt"
        
        self.write({
            'file_data': encoded_data,
            'file_name': filename,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_ve.payroll.bank.export.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def _get_clean_identification(self, employee):
        val = employee.identification_id or employee.ssnid or '0'
        clean_id = ''.join(filter(str.isdigit, str(val)))
        return clean_id if clean_id else '0'

    def _get_clean_account(self, employee):
        acc = employee.bank_account_id.acc_number if employee.bank_account_id else ''
        clean_acc = ''.join(filter(str.isdigit, str(acc)))
        return clean_acc.zfill(20)

    def _generate_bdv_txt(self, company_acc):
        # Format Banco de Venezuela TXT (Fixed length lines)
        # Line format: Header and detail rows
        lines = []
        # Header line (BDV format: H + company_acc + count + total_amount)
        total_amount = sum(slip.net_wage for slip in self.payslip_ids)
        total_centimos = int(round(total_amount * 100))
        count = len(self.payslip_ids)
        
        header = f"H{company_acc}{str(count).zfill(5)}{str(total_centimos).zfill(15)}"
        lines.append(header)
        
        for slip in self.payslip_ids:
            emp = slip.employee_id
            cid = self._get_clean_identification(emp).zfill(10)
            emp_acc = self._get_clean_account(emp)
            emp_amount = int(round(slip.net_wage * 100))
            name = (emp.name or '').upper()[:30].ljust(30)
            
            # BDV detail line: D + cedula + nombre + cuenta + monto
            row = f"D{cid}{name}{emp_acc}{str(emp_amount).zfill(15)}"
            lines.append(row)
            
        return lines

    def _generate_banesco_txt(self, company_acc):
        # Format Banesco CSV/TXT (Comma separated values or fixed format)
        lines = []
        for slip in self.payslip_ids:
            emp = slip.employee_id
            cid = self._get_clean_identification(emp)
            emp_acc = self._get_clean_account(emp)
            amount_str = f"{slip.net_wage:.2f}"
            name = (emp.name or '').upper()[:40]
            
            # Format: V/E, Cedula, Nombre, Cuenta (20), Monto, Ref
            row = f"V,{cid},{name},{emp_acc},{amount_str},PAGO NOMINA"
            lines.append(row)
            
        return lines

    def _generate_mercantil_txt(self, company_acc):
        # Format Mercantil TXT
        lines = []
        for slip in self.payslip_ids:
            emp = slip.employee_id
            cid = self._get_clean_identification(emp).zfill(10)
            emp_acc = self._get_clean_account(emp)
            amount_str = f"{slip.net_wage:.2f}".replace('.', ',')
            
            row = f"{company_acc};{cid};{emp_acc};{amount_str};NOMINA"
            lines.append(row)
            
        return lines

    def _generate_provincial_txt(self, company_acc):
        # Format BBVA Provincial TXT
        lines = []
        for slip in self.payslip_ids:
            emp = slip.employee_id
            cid = self._get_clean_identification(emp).zfill(10)
            emp_acc = self._get_clean_account(emp)
            amount_centimos = str(int(round(slip.net_wage * 100))).zfill(12)
            
            row = f"02{cid}{emp_acc}{amount_centimos}001"
            lines.append(row)
            
        return lines
