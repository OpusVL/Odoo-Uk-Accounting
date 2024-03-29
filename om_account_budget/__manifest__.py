# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Odoo 13 Budget Management',
    'author': 'Odoo Mates, Odoo SA',
    'category': 'Accounting',
    'description': """Use budgets to compare actual with expected revenues and costs""",
    'summary': 'Odoo 13 Budget Management',
    'depends': ['account', 'web'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'security/account_budget_security.xml',
        'views/account_analytic_account_views.xml',
        'views/account_budget_views.xml',
        'views/res_config_settings_views.xml',
        'views/webclient_templates.xml',
    ],
    'qweb': [
        'static/src/xml/base.xml',
    ],
    "images": ['static/description/banner.gif'],
    'demo': ['data/account_budget_demo.xml'],
}
