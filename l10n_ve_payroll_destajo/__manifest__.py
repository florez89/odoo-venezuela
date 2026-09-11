# -*- coding: utf-8 -*-
{
    'name': 'Nómina Venezuela - Producción a Destajo (LOTTT Art. 114)',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll/Localization',
    'summary': 'Control de producción por pieza/destajo, cortes y liquidación semanal en USD a tasa BCV',
    'description': """
Módulo de Gestión de Producción a Destajo y Unidad de Obra (LOTTT Art. 114)
===========================================================================
- 100% Configurable desde UI para cualquier rubro (textil, calzado, ensamble, manufactura).
- Catálogo de productos, modelos y prendas con sus operaciones y tarifas en USD.
- Control de lotes de corte y producción con validación de mermas y sobreproducción.
- Planilla semanal de registro rápido de piezas por trabajador.
- Soporte para destajo puro (100% producción) y esquemas mixtos (sueldo fijo + destajo/comisión).
- Integración directa con recibos de nómina a tasa oficial BCV.
    """,
    'author': 'TuContabilidad.Online',
    'website': 'https://tucontabilidad.online',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'hr_payroll', 'l10n_ve_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'data/destajo_salary_rule_data.xml',
        'data/prenda_initial_data.xml',
        'views/destajo_producto_views.xml',
        'views/destajo_lote_views.xml',
        'views/destajo_semanal_views.xml',
        'views/destajo_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
