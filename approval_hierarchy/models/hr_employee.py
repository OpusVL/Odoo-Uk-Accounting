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
                if role_action and role_action[0].min_value <= value <= role_action[0].max_value:
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
                CUSTOM_ERROR_MESSAGES.get('approve') % self._description)
        if self.job_id and self.job_id.state == 'approved':
            self.update_user_groups(self.job_id)
        return self.with_context(supplier_action=True).write(
            {'state': 'approved'}
        )

    def update_user_groups(self, job):
        """
        @param job: hr.job recordset
        Propagate the roles defined against the `job`s role ids to the
        users which are linked to the employee(s) under self
        """
        users = self.mapped('user_id')
        groups = self.env['res.groups']
        all_groups = groups.search([
            ('approval_group', '=', True)
        ])
        checked_roles = job.job_role_ids.filtered(
                lambda role: role.permission)
        for checked_role in checked_roles:
            groups |= checked_role.role_action_id
            users.write(dict(groups_id=[(4, checked_role.role_action_id.id)]))
        unchecked_groups = all_groups.filtered(
                lambda group: group not in groups)
        for unchecked_group in unchecked_groups:
            users.write(dict(groups_id=[(3, unchecked_group.id)]))
        amend_approve_system_users = self.env.ref(
            'approval_hierarchy.group_amend_system_users')
        amend_approve_system_users |= self.env.ref(
            'approval_hierarchy.group_approve_system_users')
        common = set(unchecked_groups).intersection(
            set(amend_approve_system_users))
        if common == set(amend_approve_system_users):
            users.write(dict(
                groups_id=[(3, self.env.ref('hr.group_hr_manager').id)]))
        return True

    def action_reject(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_approve_system_users"):
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('reject') % self._description)
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
        # I tried to transfer this hook on BaseModel but the record
        # state was not changing
        fields_to_be_tracked = helpers.get_fields_to_be_tracked()
        if fields_to_be_tracked.get(
                self._name) and any(field in vals for field in
                                    fields_to_be_tracked.get(self._name)) and \
                not self._context.get('supplier_action'):
            vals['state'] = 'draft'
        return super(HrEmployee, self).write(vals)


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    delegated_user_id = fields.Many2one(readonly=True)
