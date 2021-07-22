from odoo.addons.approval_hierarchy import helpers

def migrate(cr, installed_version):
    helpers.reset_config_settings_sysparam(cr)
