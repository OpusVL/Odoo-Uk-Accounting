# -*- coding: utf-8 -*-

from odoo import fields, models


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    delegated_user_id = fields.Many2one(
        'res.users',
        string='Delegated User',
    )


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('waiting', 'Waiting'),
            ('rejected', 'Rejected'),
            ('approved', 'Approved')
        ],
        string='Status',
        readonly=True,
        copy=False,
        default='draft',
        tracking=True,
    )

    def get_approved_user(self, action):
        approval_user_id = False
        found = False
        employee = self
        if self.state != 'approved':
            return False
        while not found and employee:
            # Checks if employee has approval rights
            has_approval_rights = employee.check_if_has_approval_rights(
                action)
            if has_approval_rights:
                found = True
                delegated_user = employee.user_id.delegated_user_id
                if delegated_user:
                    while delegated_user:
                        approval_user_id = delegated_user
                        delegated_user = delegated_user.delegated_user_id
                else:
                    approval_user_id = employee.user_id
            else:
                # Replace with employee manager and next loop it will
                # controll if his manager has approval rights
                employee = employee.parent_id
        return approval_user_id

    def check_if_has_approval_rights(self, action):
        if not self.user_id or not self.job_id or not \
                self.job_id.state == 'approved' or not self.state == 'approved':
            return False
        else:
            role_action = self.job_id.job_role_ids.filtered(
                lambda r: r.role_action_id == action and r.permission)
            if role_action:
                return True
            else:
                return False


