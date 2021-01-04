# -*- coding: utf-8 -*-

##############################################################################
#
# Check UK Vat Number
# Copyright (C) 2020 OpusVL (<http://opusvl.com/>)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'UK HMRC MTD - VAT Check',
    'version': '9.0.1',
    'author': 'OpusVL',
    'website': 'https://opusvl.com/',
    'summary': 'This module enables Odoo Community and Enterprise to Check Vat Details of Company and Business.',
    'category': 'accounting',
    'description': 'This module enables Odoo Community and Enterprise to Check Vat Details of Company and Business.',
    'images': ['static/description/MTD-Connector.png'
    ],
    'depends': [
        'base',
        'account',
        'mail',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'wizard/vat_check_wizard_view.xml',
        'views/res_partner_view.xml',
        'views/mtd_menu.xml',
        'views/hmrc_configuration_view.xml',
        'views/vat_number_history_view.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'application': True,
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
