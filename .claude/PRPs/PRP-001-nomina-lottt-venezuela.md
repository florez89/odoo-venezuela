# PRP-001: Localización Nómina Venezuela (LOTTT) al estilo Profit Plus para Odoo 19

> **Estado**: EN DESARROLLO (Ampliación Fases 10, 11 y 12)
> **Fecha de Inicio**: 2026-07-14
> **Fecha de Actualización**: 2026-07-20
> **Proyecto**: Odoo 19 / Localización Venezuela (l10n_ve_payroll)
> **Criterio rector**: Evitar por completo el hardcodeo de reglas y porcentajes de ley. Implementar un sistema paramétrico dinámico con vigencia temporal, adaptado a las regulaciones de 2026 (Ley de Pensiones de 2024, indexación de Cesta Ticket, salarios en divisas, ISLR, Liquidaciones de Ley, Horas Extras/Feriados LOTTT, Préstamos a Trabajadores y TXT Bancarios), basado en la ingeniería inversa de las fórmulas y procesos de Profit Plus.

---

## Objetivo

Implementar un módulo de nómina localizada para Venezuela (`l10n_ve_payroll`) en Odoo 19 que sea dinámico, paramétrico e intuitivo para el usuario. Debe calcular los conceptos de la LOTTT y deducciones de ley vigentes al 2026 utilizando un panel de configuración sin código (cero hardcoding), permitiendo el procesamiento de contratos en USD o VES a tasa oficial BCV, la retención de I.S.L.R. mediante planilla AR-I, la gestión del Libro Auxiliar de Prestaciones, Liquidaciones de Ley, gestión de Horas Extras/Feriados, Préstamos a trabajadores y generación de TXT bancarios.

---

## Por Qué

| Problema | Solución |
|----------|----------|
| Las regulaciones de nómina en Venezuela cambian con frecuencia (porcentajes de aportes, topes de cotización, valor de la Unidad Tributaria, Cesta Ticket indexado). Hardcodear estos valores en reglas salariales hace que el módulo sea obsoleto al primer cambio legal. | Crear un modelo de configuración histórica y temporal (`l10n_ve.payroll.parameter`) con una vista de usuario (UI/UX) muy limpia, de modo que el usuario actualice las constantes (como el salario mínimo, la UT o el 9% de la Ley de Pensiones) sin tocar código. |
| La base clonada de Odoo (2017) no cubre las reformas recientes, tales como la **Ley de Protección de las Pensiones (LPP)** promulgada en **mayo de 2024** (aporte patronal del 9%) ni la indexación de beneficios. | Diseñar la nómina desde cero cubriendo todo el marco legal de 2026, incluyendo la LPP de 2024 y el Ingreso Mínimo Integral Indexado. |
| El estándar de facto en Venezuela, Profit Plus Nómina, es muy técnico y su UI está desactualizada. Los usuarios buscan una alternativa moderna y fluida con paridad operativa total. | Diseñar una experiencia de usuario (UX) sobresaliente en Odoo 19: contratos claros, asignación automática de novedades, préstamos, horas extras LOTTT, TXT bancarios y un recibo de pago PDF impecable. |

**Valor de negocio**: Cumplimiento legal del 100% de la nómina venezolana en 2026, permitiendo a las empresas auditar sus costos en USD/VES, gestionar retenciones fiscales de I.S.L.R., provisionar mensualmente prestaciones sociales e intereses según el BCV, emitir liquidaciones de fin de relación laboral, procesar novedades de recargos por horas extras/feriados, administrar préstamos con descuento automático por nómina y generar archivos planos TXT para pago masivo en bancos venezolanos.

---

## Qué

### Criterios de Éxito
- [x] **Configuración Paramétrica (`l10n_ve.payroll.parameter`):**
  - Panel de control (vista de lista y formulario) para registrar parámetros por fecha de inicio y fin (con restricción para evitar solapes de fechas).
  - Campos parametrizados: Salario Mínimo Nacional, Unidad Tributaria (UT), Cesta Ticket Base (USD), Alícuota LPP 2024 (9% patronal) y base mínima, Porcentajes IVSS (4% empleado, 9% patronal), Porcentajes SPF (0.5% empleado, 2% patronal), Porcentaje FAOV (1% empleado, 2% patronal), Porcentaje INCES (2% patronal, 0.5% empleado), días base e históricos de Vacaciones y Utilidades, y esquema de prestaciones.
- [x] **Soporte Multimoneda / Indexación (USD/VES):**
  - Contratos con salario base negociado en dólares (`USD`) o bolívares (`VES`).
  - Cálculo dinámico a la tasa BCV del periodo final del recibo de nómina (`date_to`).
  - Cálculo del Cesta Ticket Socialista indexado proporcionalmente a la asistencia.
- [x] **Nuevas Regulaciones Vigentes y Seguro Social (IVSS/SPF/LPP):**
  - Implementar la **Ley de Protección de Pensiones de 2024** (aporte patronal del 9% sobre total de ingresos ordinarios con base mínima indexada de $240 USD).
  - IVSS y SPF calculados dinámicamente por la cantidad de lunes transcurridos en el periodo de nómina.
- [x] **Vacaciones, Utilidades e INCES (Fases 5 y 6):**
  - Reglas de Vacaciones (VAC), Bono Vacacional (BON_VAC) y Utilidades (UTIL) calculados de forma automática según la antigüedad del trabajador u overrides manuales.
  - Aporte INCES del 2% patronal sobre salarios ordinarios y retención del 0.5% del trabajador sobre pagos de Utilidades de Ley.
- [x] **Libro Auxiliar de Prestaciones e Intereses BCV (Fase 7):**
  - Registro dinámico y transparente en el Libro Auxiliar (`l10n_ve.prestaciones.ledger`) que rastrea aportes por garantía (mensual o trimestral), días adicionales por antigüedad e intereses devengados según las tasas mensuales oficiales del BCV (`l10n_ve.prestaciones.rate`).
- [x] **Retención de I.S.L.R. y Planilla AR-I (Fase 8):**
  - Declaración estimada en planilla AR-I (`l10n_ve.ari`) calculando deducciones, cargas familiares y porcentaje de retención progresivo basado en la Tarifa 1 de la Ley del I.S.L.R.
  - Deducción automática (`DED_ISLR`) en los recibos de nómina según la tasa AR-I activa.
- [x] **Liquidaciones de Ley y Fin de Relación Laboral (Fase 9):**
  - Wizard para preparar egreso (Fecha, motivo de salida: renuncia, despido injustificado, etc.).
  - Liquidación que calcula el acumulado del libro auxiliar (`LIQ_GAR`) y lo compara con el cálculo retroactivo del Art. 142 de la LOTTT (`LIQ_RET`), pagando el mayor de ambos (`LIQ_DIF`).
  - Cálculo de conceptos fraccionados de ley (vacaciones, bono vacacional y utilidades fraccionadas) e indemnización por despido injustificado (Art. 92, doble indemnización).
- [ ] **Horas Extras, Recargo Nocturno y Días Feriados LOTTT (Fase 10):**
  - Reglas salariales para Horas Extras Diurnas (`HED` +50% recargo Art. 118), Horas Extras Nocturnas (`HEN` +30% recargo nocturnal + 50% extra Art. 117 y 118) y Días Feriados / Descanso Trabajados (`FER_TRAB` +150% recargo Art. 120).
- [ ] **Módulo de Préstamos y Avances a Trabajadores (Fase 11):**
  - Modelo `l10n_ve.loan` y cuotas `l10n_ve.loan.line`. Descuento automático de cuota en el recibo de nómina (`DED_PRESTAMO`) y actualización del saldo pendiente del préstamo.
- [ ] **Generador de Archivos TXT Bancarios para Nómina (Fase 12):**
  - Wizard `l10n_ve.payroll.bank.export.wizard` para seleccionar banco (Banco de Venezuela, Banesco, Mercantil, Provincial), contrato y periodo, generando el archivo plano `.txt` con los formatos bancarios venezolanos oficiales.

---

## Contexto e Ingeniería Inversa de Profit Plus

Se auditó la base de datos de Profit Plus Nómina (`DEMON`), extrayendo los parámetros y las fórmulas exactas en C# para garantizar una paridad técnica total en Odoo:

### 1. Parámetros del Sistema (`snconst`)

| Código | Descripción en Profit Plus | Valor de Referencia | Mapeo en Odoo 19 |
|--------|----------------------------|---------------------|------------------|
| **`R001`** | Factor IVSS (Trabajador) | 4.0% | `ivss_employee_rate` |
| **`U001`** | Factor IVSS (Patronal) | 9.0% | `ivss_employer_rate` (según riesgo) |
| **`T003`** | Tope Salarios Mínimos IVSS | 5 | `ivss_limit_weeks` |
| **`R002`** | Factor SPF / Paro Forzoso (Trabajador) | 0.5% | `spf_employee_rate` |
| **`U002`** | Factor SPF / Paro Forzoso (Patronal) | 1.7% / 2.0% | `spf_employer_rate` |
| **`T004`** | Tope Salarios Mínimos SPF | 5 / 10 | `spf_limit_weeks` |
| **`R003`** | Factor LPH / FAOV (Trabajador) | 1.0% | `faov_employee_rate` |
| **`U003`** | Factor LPH / FAOV (Patronal) | 2.0% | `faov_employer_rate` |
| **`U004`** | Factor INCES (Patronal) | 2.0% | `inces_employer_rate` |
| **`R004`** | Factor INCES (Trabajador) | 0.5% (sobre utilidades) | `inces_employee_rate` |
| **`C019`** | Recargo por Bono Nocturno (%) | 30.0% | Recargo de Bono Nocturno (Art. 156 LOTTT) |

### 2. Fórmulas de Cálculo Originales (C#) vs. Lógica en Odoo (Python)

#### A. Seguro Social Obligatorio (IVSS - `R001`)
*   **Fórmula C# (Profit):**
    ```csharp
    return Math.Round(Math.Min(const_T003 * (Decimal)Info_Doc.valor_Tabla(7, Fecha_Fin_Nomina, 0), Concepto(typeof(C_Q024))) * 12 / 52 * const_R001 / 100 * Concepto(typeof(C_Y003)), 2);
    ```
*   **Equivalencia en Odoo (Python):**
    ```python
    base = min(limit_salary, contract.wage)
    weekly_base = (base * 12) / 52
    result = round(weekly_base * (ivss_rate / 100.0) * mondays_count, 2)
    ```

#### B. Ley de Vivienda y Hábitat (FAOV - `R003`)
*   **Fórmula C# (Profit):**
    ```csharp
    decimal total = Info_Doc.conceptos_valor_acumulado("C_Q023", Info_Doc.pri_mes(Fecha_Ini_Nomina), Fecha_Ini_Nomina.AddDays(-1), null);
    decimal total2 = Concepto(typeof(C_Q023));
    decimal totalR003 = const_S017.Equals("S") ? total + total2 : total2;
    return totalR003 * const_R003 / 100;
    ```
*   **Equivalencia en Odoo (Python):**
    Odoo evalúa el salario del periodo más los complementos salariales (según Art. 104 de la LOTTT) acumulados del mes y aplica la alícuota sobre el salario bruto real sin topes.

#### C. Ley de Protección de las Pensiones de 2024 (LPP) - Nuevo en 2024
*   **Lógica de Negocio:**
    Aporte del 9% patronal sobre la base imponible (sueldo bruto), con piso mínimo de $240 USD (a tasa BCV oficial) por trabajador.
*   **Fórmula en Odoo (Python):**
    ```python
    base_lpp = max(minimum_pension_base_ves, total_worker_income_ves)
    result = round(base_lpp * (pension_rate / 100.0), 2)
    ```

---

## Blueprint (Assembly Line)

- [x] **Fase 1: Panel de Parámetros Históricos (`l10n_ve.payroll.parameter`)**
  - **Objetivo**: Crear la tabla y la interfaz de usuario para registrar los valores y porcentajes de ley históricos sin solapamiento de fechas.
  - **Resultado**: Modelo e interfaz implementados en [l10n_ve_payroll_parameter.py](file:///C:/Dev/Odoo/LocalizacionVe/l10n_ve_payroll/models/l10n_ve_payroll_parameter.py) y vistas de control.
- [x] **Fase 2: Contratos Multimoneda y Gestión Cambiaria**
  - **Objetivo**: Extender el empleado para soportar salarios en USD, y el recibo de nómina para registrar la tasa BCV del periodo y calcular el salario base en VES.
  - **Resultado**: Lógica integrada en [hr_employee.py](file:///C:/Dev/Odoo/LocalizacionVe/l10n_ve_payroll/models/hr_employee.py) y [hr_payslip.py](file:///C:/Dev/Odoo/LocalizacionVe/l10n_ve_payroll/models/hr_payslip.py).
- [x] **Fase 3: Reglas de Devengo (LOTTT y Cesta Ticket)**
  - **Objetivo**: Programar las reglas de asignación y el Cesta Ticket Socialista indexado proporcionalmente a la asistencia del periodo.
  - **Resultado**: Regla de Cesta Ticket `BON_ALIM` implementada de forma dinámica en [hr_payslip.py](file:///C:/Dev/Odoo/LocalizacionVe/l10n_ve_payroll/models/hr_payslip.py).
- [x] **Fase 4: Deducciones y Aportes Patronales (IVSS, SPF, FAOV y Pensiones 2024)**
  - **Objetivo**: Programar las deducciones con cálculo dinámico de lunes en el mes. Implementar la retención de la Ley de Pensiones (9% patronal) con su base mínima indexada de $240 USD.
  - **Resultado**: Reglas creadas y testeadas en [hr_salary_rule_data.xml](file:///C:/Dev/Odoo/LocalizacionVe/l10n_ve_payroll/data/hr_salary_rule_data.xml).
- [x] **Fase 5: Aporte y Retención INCES**
  - **Objetivo**: Retener 0.5% del trabajador sobre utilidades/bonificaciones de fin de año y aportar el 2% patronal sobre salarios.
  - **Resultado**: Reglas `APO_INCES` y `DED_INCES` implementadas.
- [x] **Fase 6: Vacaciones y Utilidades de Ley**
  - **Objetivo**: Automatizar días y bonos por antigüedad (LOTTT Art 131, 190, 192) y dar soporte a overrides de entrada manual.
  - **Resultado**: Métodos en `hr_payslip` y reglas `VAC`, `BON_VAC` y `UTIL` implementadas.
- [x] **Fase 7: Garantía de Prestaciones e Intereses BCV**
  - **Objetivo**: Registro del Fideicomiso en Libro Auxiliar (Ledger) calculando el salario integral y el devengo mensual de intereses por tasas BCV.
  - **Resultado**: Modelos `l10n_ve.prestaciones.ledger` y `l10n_ve.prestaciones.rate` operativos.
- [x] **Fase 8: Retención de I.S.L.R. y Planilla AR-I**
  - **Objetivo**: Calcular el porcentaje de retención progresivo inicial mediante la planilla AR-I (Tarifa 1) y aplicarlo mensualmente.
  - **Resultado**: Planilla `l10n_ve.ari` y regla `DED_ISLR` implementadas y verificadas.
- [x] **Fase 9: Liquidación de Prestaciones Sociales y Fin de Relación Laboral**
  - **Objetivo**: Automatizar el finiquito comparando Garantía acumulada vs Cálculo Retroactivo LOTTT Art. 142 literal c, fraccionados e indemnización por despido injustificado (Art. 92).
  - **Resultado**: Asistente de egreso y reglas de liquidación (`LIQ_GAR`, `LIQ_RET`, `LIQ_DIF`, fraccionados y `LIQ_IND_DESP`) implementados y validados.
- [ ] **Fase 10: Novedades de Horas Extras, Recargo Nocturno y Días Feriados LOTTT**
  - **Objetivo**: Crear tipos de input (`HED_HOURS`, `HEN_HOURS`, `FER_DAYS`) y reglas salariales para H.E. Diurnas (+50%), H.E. Nocturnas (+30% nocturnal + 50% extra = 80% recargo) y Feriados trabajados (+150% recargo según Art. 117, 118, 120 LOTTT).
  - **Resultado**: Reglas salariales `ASIG_HED`, `ASIG_HEN` y `ASIG_FER` en `hr_salary_rule_data.xml`.
- [ ] **Fase 11: Módulo de Préstamos y Descuento por Cuotas**
  - **Objetivo**: Modelo `l10n_ve.loan` y `l10n_ve.loan.line` para registrar préstamos otorgados y descontar cuotas activas automáticamente en el recibo (`DED_PRESTAMO`).
  - **Resultado**: Modelos, vistas y regla salarial `DED_PRESTAMO` implementados.
- [ ] **Fase 12: Exportador de TXT Bancarios para Nómina**
  - **Objetivo**: Wizard `l10n_ve.payroll.bank.export.wizard` para generar el archivo TXT formateado para pago masivo de nómina en Banco de Venezuela, Banesco, Mercantil y Provincial.
  - **Resultado**: Wizard y generador de archivos `.txt` implementados.

---

## Estructura Final del Módulo
```text
l10n_ve_payroll/
├── __init__.py
├── __manifest__.py
├── data/
│   └── hr_salary_rule_data.xml                  # Reglas salariales venezolanas (Fases 3-9)
├── models/
│   ├── __init__.py
│   ├── hr_employee.py                           # Ficha del empleado (multimoneda, balances, egreso)
│   ├── hr_payslip.py                            # Tasa BCV, integrales, ganchos de cierre de liquidación
│   ├── l10n_ve_payroll_parameter.py             # Parámetros históricos de nómina
│   ├── l10n_ve_prestaciones_rate.py             # Tasas de interés de prestaciones BCV
│   ├── l10n_ve_prestaciones_ledger.py           # Libro auxiliar de prestaciones
│   ├── l10n_ve_ari.py                           # Planilla AR-I para ISLR
│   └── l10n_ve_employee_liquidation_wizard.py   # Asistente para egreso de trabajadores
├── security/
│   └── ir.model.access.csv                      # Permisos y seguridad ACL
├── tests/
│   ├── __init__.py
│   └── test_salary_rules.py                     # Suite de pruebas automatizadas (Casos A al I)
├── views/
│   ├── hr_employee_views.xml                    # Vistas extendidas del empleado (pestañas y botones)
│   ├── hr_payslip_views.xml                     # Tasa BCV y sueldos en el recibo de nómina
│   ├── l10n_ve_payroll_parameter_views.xml      # Formulario paramétrico dinámico
│   ├── l10n_ve_prestaciones_rate_views.xml      # Menú y tablas de tasas BCV de prestaciones
│   ├── l10n_ve_prestaciones_ledger_views.xml    # Visualización del Libro Auxiliar
│   ├── l10n_ve_ari_views.xml                    # Formularios e historiales de planillas AR-I
│   └── l10n_ve_employee_liquidation_wizard_views.xml # Formulario del wizard de egreso
└── manual_usuario.pdf                           # Manual del usuario completo compilado en PDF
```

---

## Gotchas

- **Faltas / Reposos:** Las faltas injustificadas descuentan el Cesta Ticket proporcionalmente. Los reposos médicos y otras inasistencias en Odoo se gestionan mediante las líneas de "Worked Days" (WORK100, OUT, etc.) de forma nativa, deduciendo proporcionalmente el salario básico y los conceptos asociados.
- **Base Imponible de la Ley de Pensiones (2024):** No solo aplica al salario básico, sino también a todos los ingresos ordinarios del trabajador en el recibo de nómina. Esto se programó en la regla `APO_LPP` utilizando el total del salario imponible (Gross Salary) del recibo de nómina, con un mínimo indexado correspondiente a 240.00 VES indexado al BCV.
- **Base de Cálculo del ISLR:** Por defecto, la retención de ISLR se calcula sobre el Salario Bruto (Gross) del periodo. Conceptos no salariales (como el Cesta Ticket) se excluyen de forma automática de la base al no formar parte de la categoría salarial gravable.

---

## Anti-Patrones

- **NUNCA** hardcodear valores porcentuales como `0.04` (IVSS) o `0.09` (Pensiones) directamente en las fórmulas de Python de las reglas salariales. Siempre se debe hacer `parameter_id.ivss_employee_rate` o similar.
- Evitar usar el plan de cuentas de forma rígida; el módulo de nómina debe mapear las cuentas mediante diarios de nómina estándar.

---

## Verificación de Calidad y Pruebas
100% de la suite de pruebas del archivo `test_salary_rules.py` pasa con éxito en el servidor de base de datos de producción:
*   **Caso A:** Sueldo básico y Cesta Ticket proporcional.
*   **Caso B:** Inasistencias / días fuera de contrato.
*   **Caso C:** Retención INCES (0.5%) sobre pagos de Utilidades.
*   **Caso D:** Cálculos semanales topados de Seguro Social (IVSS, SPF, FAOV, LPP).
*   **Caso E & F:** Cálculos de Garantía de Prestaciones (mensual/trimestral), alícuotas integrales y Libro Auxiliar.
*   **Caso G:** Cálculos estimados de Planilla AR-I y retención `DED_ISLR`.
*   **Caso H:** Liquidación de prestaciones por renuncia (fraccionados y cálculo de retroactividad LOTTT).
*   **Caso I:** Liquidación por despido injustificado (doble indemnización LOTTT Art. 92).
