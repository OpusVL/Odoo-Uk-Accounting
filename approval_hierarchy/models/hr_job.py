# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.approval_hierarchy import helpers
from odoo.addons.approval_hierarchy.helpers import CUSTOM_ERROR_MESSAGES


class HrJobRole(models.Model):
    _name = 'hr.job.role'
    _description = 'Job roles'

    name = fields.Char(string='Name', required=True, )
    role_action_id = fields.Many2one(
        'res.groups',
        string='Role',
        required=True,
        domain=[('approval_group', '=', True)]
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

    @api.model
    def create(self, vals):
        res = super(HrJobRole, self).create(vals)
        if vals:
            message = "Job role {} has been created.".format(
                res.name)
            # There is no need to control if res.job_id because is a
            # one2many field and always will have value
            res.job_id.message_post(body=message)
        return res

    def unlink(self):
        for role in self:
            message = "Job role {} has been deleted.".format(
                role.name)
            role.job_id.message_post(body=message)
        return super(HrJobRole, self).unlink()

    @api.constrains('min_value', 'max_value')
    def _verify_values(self):
        for role in self:
            if role.max_value and role.min_value and role.min_value > role.max_value:
                raise ValidationError(_(
                    "Min value must be equal or smaller than max value."))
            if role.permission and role.enable_value and role.min_value <= 0:
                raise ValidationError(_(
                    "Min value must be greater than 0."))
            if role.permission and role.enable_value and role.max_value <= 0:
                raise ValidationError(_(
                    "Max value must be greater than 0."))

    @api.onchange('role_action_id')
    def onchange_role_action_id(self):
        self.name = self.role_action_id and self.role_action_id.name or ''

    @api.onchange('permission')
    def onchange_permission(self):
        self.min_value = 0.0
        self.max_value = 0.0


class HrJob(models.Model):
    _name = 'hr.job'
    _inherit = ['hr.job', 'mail.thread', 'mail.activity.mixin']

    job_role_ids = fields.One2many(
        'hr.job.role',
        'job_id',
        string='Job Roles',
    )
    state = fields.Selection(
        selection_add=[
            ('draft', 'Draft'),
            ('waiting', 'Waiting'),
            ('rejected', 'Rejected'),
            ('approved', 'Approved')
        ],
        default='draft',
    )

    def request_approval(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_amend_system_users"):
            raise UserError(CUSTOM_ERROR_MESSAGES.get('request'))
        return self.with_context(supplier_action=True).write({'state': 'waiting'})

    def action_approve(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_approve_system_users"):
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('approve') % 'a job position')
        self.update_user_groups()
        return self.with_context(supplier_action=True).write(
            {'state': 'approved'}
        )

    def action_reject(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_approve_system_users"):
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('reject') % 'a job position')
        return self.with_context(supplier_action=True).write(
            {'state': 'rejected'}
        )

    def set_to_draft(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_amend_system_users"):
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('write') % 'a job position')
        return self.with_context(supplier_action=True).write({'state': 'draft'})

    def update_user_groups(self):
        users = self.env['res.users']
        for employee in self.employee_ids:
            if employee.user_id not in users:
                users |= employee.user_id
        for checked_role in self.job_role_ids.filtered(
                lambda role: role.permission):
            users.write(dict(groups_id=[(4, checked_role.role_action_id.id)]))
        for unchecked_role in self.job_role_ids.filtered(
                lambda role: not role.permission):
            users.write(dict(groups_id=[(3, unchecked_role.role_action_id.id)]))
        return True

    def write(self, vals):
        if self._context.get('supplier_action'):
            return super(HrJob, self.with_context(
                supplier_action=True)).write(vals)
        elif self.env.user.has_group(
                "approval_hierarchy.group_amend_system_users"):
            fields_to_be_tracked = helpers.get_fields_to_be_tracked()
            if any(field in vals for field in
                   fields_to_be_tracked.get('hr.job')):
                vals['state'] = 'draft'
                if 'job_role_ids' in vals:
                    for job_role in vals.get('job_role_ids'):
                        if isinstance(job_role, list) and len(job_role) == 3 \
                                and isinstance(job_role[2], dict) and job_role[2] \
                                and isinstance(job_role[1], int):
                            role = self.env['hr.job.role'].browse(job_role[1])
                            message = "Changes made to the job role '{}'.".format(
                                role.name)
                            # I could not find a way to make these lines look
                            # better, without if-s
                            data = job_role[2]
                            message_mapping = {
                                'permission': '\nPermission: {}'.format(
                                    data.get('permission')),
                                'min_value': '\nMin Value: {}'.format(
                                    data.get('min_value')),
                                'max_value': '\nMax Value: {}'.format(
                                    data.get('max_value')),
                            }
                            for message_type, message_str in message_mapping.items():
                                if message_type in data:
                                    message += message_str
                            self.message_post(body=message)
            return super(HrJob, self.with_context(
                supplier_action=True)).write(vals)
        else:
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('write') % 'a job position')
