# -*- coding: utf-8 -*-

##############################################################################
#
# Approval Hierarchy
# Copyright (C) 2020 Opus Vision Limited (<https://opusvl.com>)
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
    'name': "Approval Hierarchy",

    'summary': 'Manage approval hierarchy',
    
    'category': 'Tools',
    
    'description': """Manage approval hierarchy
""",

    'author': "OpusVL limited",
    'website': "https://opusvl.com",

    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['uk_accounting', 'hr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/approval_hierarchy_security.xml',
        'data/job_role_action_data.xml',
        'data/data.xml',
        'views/hr_job_views.xml',
        'views/res_users_views.xml',
    ],
}