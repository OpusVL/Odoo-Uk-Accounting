# -*- coding: utf-8 -*-

##############################################################################
#
# UK Accounting Localization
# Copyright (C) 2019 Opus Vision Limited (<https://opusvl.com>)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': "UK Accounting Localization",

    'summary': 'UK Accounting :Localization',
    
    'category': 'Accounting',
    
    'description': """UK Accounting :Localization
""",

    'author': "OpusVL limited",
    'website': "https://opusvl.com",

    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account', 'base_iban', 'base_vat'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/uk_accounting_security.xml',
        'data/uk_accounting_chart_data.xml',
        'data/account_type_data.xml',
        'data/account.account.template.csv',
        'data/account.chart.template.csv',
        'data/account.tax.group.csv',
        'data/account_tax_report_data.xml',
        'data/account_tax_data.xml',
        'data/account_chart_template_data.xml',
        'data/ir_sequence_data.xml',
        'views/account_account_view.xml',
        'views/account_move_view.xml',
    ],
}
