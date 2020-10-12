# -*- coding: utf-8 -*-
from . import controllers
from . import models
from . import wizards
from odoo import api, SUPERUSER_ID
from odoo.addons import account

original_auto_install_l10n = account._auto_install_l10n

def _auto_install_l10n(cr, registry):

    env = api.Environment(cr, SUPERUSER_ID, {})
    country_code = env.company.country_id.code

    if country_code and country_code == 'GB':
        module_ids = env['ir.module.module'].search([
            ('name', '=', 'uk_accounting'),
            ('state', '=', 'uninstalled'),
        ])
        module_ids.sudo().button_install()

    else:
        return original_auto_install_l10n(cr, registry)

account._auto_install_l10n = _auto_install_l10n
