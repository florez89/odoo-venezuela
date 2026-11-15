from . import models
from . import wizard
from . import report

from odoo.tools import sql

old_module = "binaural_accountant"
new_module = "l10n_ve_accountant"

def pre_init_hook(env):
    reassign_account_data_ids(env.cr)
    reassign_tax_unit_data_ids(env.cr)
    add_foreign_rate_date_column(env.cr)


def add_foreign_rate_date_column(cr):
    """Create account_move.foreign_rate_date before the ORM does.

    The field shares `_compute_rate` with foreign_rate/foreign_inverse_rate:
    if the ORM created the column it would recompute the three fields on every
    existing move and overwrite the rates already posted. Existing moves keep
    an empty date, so they never show the outdated rate warning.
    """
    if sql.table_exists(cr, "account_move") and not sql.column_exists(
        cr, "account_move", "foreign_rate_date"
    ):
        sql.create_column(cr, "account_move", "foreign_rate_date", "date")

def reassign_account_data_ids(env):
    execute_script_sql(env, "alternative_")
    
def reassign_tax_unit_data_ids(env):
    tax_unit_data = {
        "tax_unit_data_binaural_payment_extension":"tax_unit_data_l10n_ve_payment_extension"        
    }
    
    for old_name, new_name in tax_unit_data.items():
        execute_script_sql_two(env, new_name, old_name)
    
def execute_script_sql(env, xml_id_prefix): 
    env.execute(
        """
        UPDATE ir_model_data
        SET module=%s
        WHERE module=%s AND name LIKE %s
        """,
        (new_module, old_module, f"{xml_id_prefix}%"),
    )
    
def execute_script_sql_two(env, new_name, old_name): 
    
    env.execute(
        """
        UPDATE ir_model_data
        SET module=%s, name=%s
        WHERE name=%s
        """,
        (new_module, new_name, old_name)
    )