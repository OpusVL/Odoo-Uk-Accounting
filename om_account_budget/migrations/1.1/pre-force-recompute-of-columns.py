from odoo.tools.sql import column_exists
def migrate(cr, installed_version):
    columns_to_recompute = [
        'practical_amount',
        'difference_amount',
    ]
    for column in columns_to_recompute:
        if column_exists(cr, 'crossovered_budget_lines', column):
            # This is not SQLi because the input list is trusted (i.e. in the code itself)
            cr.execute(
                'ALTER TABLE "crossovered_budget_lines" DROP COLUMN "{}"'.format(column)
            )
