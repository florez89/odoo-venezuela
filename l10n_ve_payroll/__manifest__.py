# -*- coding: utf-8 -*-
{
    'name': 'Venezuela - Nómina LOTTT',
    'summary': 'Módulo de localización para la nómina venezolana (LOTTT) y regulaciones del 2026',
    'description': """
        Módulo de nómina adaptado a la legislación de la LOTTT en Venezuela.
        Incluye:
        - Parámetros dinámicos e históricos de nómina (salario mínimo, Unidad Tributaria, topes, alícuotas).
        - Cálculo de Cesta Ticket indexado a tasa oficial BCV.
        - Retenciones de IVSS, SPF, FAOV y la nueva Ley de Protección de Pensiones de 2024.
        - Soporte para contratos multimoneda (USD/VES).
    """,
    'license': 'LGPL-3',
    'author': 'Fábrica santERP',
    'category': 'Human Resources/Payroll',
    'version': '1.0',
    'depends': ['hr_payroll', 'l10n_ve_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/l10n_ve_payroll_parameter_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_payslip_views.xml',
        'views/l10n_ve_prestaciones_rate_views.xml',
        'views/l10n_ve_prestaciones_ledger_views.xml',
        'data/hr_salary_rule_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
