# -*- coding: utf-8 -*-
{
    'name': 'Assets Management',
    'version': '13.0.0',
    'author': 'OpusVL',
    'website': 'https://opusvl.com/',
    'summary': 'Module for Assets Management',
    'category': '',
    'description': """
    Assets management
    =================
    Manage assets owned by a company.
    Keeps track of depreciations, and creates corresponding journal entries.
    """,
    'images': ['static/description/icon.png'],
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/asset_modify_views.xml',
        'views/account_asset_views.xml',
        'views/product_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'test': [
    ],
    'application': True,
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,

}
