# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.addons.approval_hierarchy import helpers
from odoo.addons.approval_hierarchy.helpers import CUSTOM_ERROR_MESSAGES


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    delegated_user_id = fields.Many2one(
        'res.users',
        string='Delegated User',
        tracking=True,
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
    )
    has_delegated = fields.Boolean(compute='_check_has_delegated')

    def _check_has_delegated(self):
        for rec in self:
            rec.has_delegated = bool(rec.delegated_user_id)

    def get_approved_user(self, action, value=0, currency=False):
        approval_user_id = False
        found = False
        employee = self
        while not found and employee:
            # Checks if employee has approval rights
            has_approval_rights = employee.check_if_has_approval_rights(
                action, value, currency)
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

    def check_if_has_approval_rights(self, action, value=0, currency=False):
        if not self.user_id or not self.job_id or not \
                self.job_id.state == 'approved' or not self.state == 'approved':
            return False
        else:
            role_access = False
            if value:
                role_action = self.job_id.job_role_ids.filtered(
                    lambda r: r.role_action_id == action and r.permission and
                              r.currency_id == currency)
                if role_action[0].min_value <= value <= role_action[0].max_value:
                    role_access = True
            else:
                role_action = self.job_id.job_role_ids.filtered(
                    lambda r: r.role_action_id == action and r.permission)
                if role_action:
                    role_access = True
            return role_access

    def request_approval(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_amend_system_users"):
            raise UserError(CUSTOM_ERROR_MESSAGES.get('request'))
        return self.with_context(supplier_action=True).write(
            {'state': 'waiting'}
        )

    def action_approve(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_approve_system_users"):
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('approve') % 'an employee')
        return self.with_context(supplier_action=True).write(
            {'state': 'approved'}
        )

    def action_reject(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_approve_system_users"):
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('reject') % 'an employee')
        return self.with_context(supplier_action=True).write(
            {'state': 'rejected'}
        )

    def set_to_draft(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_amend_system_users"):
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('write') % 'an employee')
        return self.with_context(supplier_action=True).write({'state': 'draft'})

    def write(self, vals):
        if self.env.user.is_superuser():
            return super(HrEmployee, self.with_context(
                supplier_action=True)).write(vals)
        if self._context.get('supplier_action'):
            return super(HrEmployee, self).write(vals)
        elif self._context.get('from_my_profile'):
            if self.env.user == self.user_id:
                return super(HrEmployee, self).write(vals)
            else:
                raise UserError(
                    CUSTOM_ERROR_MESSAGES.get('write') % 'an employee')
        elif self.env.user.has_group(
                "approval_hierarchy.group_amend_system_users"):
            fields_to_be_tracked = helpers.get_fields_to_be_tracked()
            if any(field in vals for field in
                   fields_to_be_tracked.get('hr.employee')):
                vals['state'] = 'draft'
            return super(HrEmployee, self.with_context(
                supplier_action=True)).write(vals)
        else:
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('write') % 'an employee')


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    delegated_user_id = fields.Many2one(readonly=True)
