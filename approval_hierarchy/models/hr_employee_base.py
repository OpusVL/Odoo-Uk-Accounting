# -*- coding: utf-8 -*-

from odoo import fields, models


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    delegated_user_id = fields.Many2one(
        'res.users',
        string='Delegated User',
    )

