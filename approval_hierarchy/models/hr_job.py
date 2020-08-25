# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class JobRoleAction(models.Model):
    _name = 'job.role.action'
    _description = 'Job Role Action'

    name = fields.Char(string='Name', required=True,)
    enable_value = fields.Boolean(string='Enable Limit Value',)


class HrJobRole(models.Model):
    _name = 'hr.job.role'
    _description = 'Job roles'

    name = fields.Char(string='Name', required=True, )
    role_action_id = fields.Many2one(
        'job.role.action',
        string='Role',
        required=True,
    )
    job_id = fields.Many2one(
        'hr.job',
        string='Job Position',
        required=True,
        ondelete='cascade',
    )
    enable_value = fields.Boolean(
        string='Enable Limit Value',
        related='role_action_id.enable_value',
        store=True
    )
    permission = fields.Boolean(string='Permission',)
    currency_id = fields.Many2one(
        'res.currency',
        'Currency',
        required=True,
        default=lambda self: self.env.company.currency_id)
    min_value = fields.Monetary(string='Min Value',)
    max_value = fields.Monetary(string='Max Value', )

    _sql_constraints = [
        (
            "role_job_unique",
            "unique (role_action_id,job_id, currency_id)",
            "Role must be unique per job !",
        )
    ]

    @api.constrains('min_value', 'max_value')
    def _verify_values(self):
        for role in self:
            if role.max_value and role.min_value and role.min_value > role.max_value:
                raise ValidationError(_(
                    "Min value must be equal or smaller than max value."))

    @api.onchange('role_action_id')
    def onchange_role_action_id(self):
        self.name = self.role_action_id and self.role_action_id.name or ''

    @api.onchange('permission')
    def onchange_permission(self):
        self.min_value = 0.0
        self.max_value = 0.0


class HrJob(models.Model):
    _inherit = 'hr.job'

    job_role_ids = fields.One2many(
        'hr.job.role',
        'job_id',
        string='Job Roles',
    )


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def get_approved_user(self, action):
        approval_user_id = False
        found = False
        employee = self
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
        if not self.user_id or not self.job_id:
            return False
        else:
            role_action = self.job_id.job_role_ids.filtered(
                lambda r: r.role_action_id == action and r.permission)
            if role_action:
                return True
            else:
                return False
