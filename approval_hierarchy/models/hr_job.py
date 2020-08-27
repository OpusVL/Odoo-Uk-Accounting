# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


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

    @api.model
    def create(self, vals):
        res = super(HrJobRole, self).create(vals)
        if vals:
            message = "Job role {} has been created.".format(
                res.name)
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
            if role.permission and role.enable_value and not role.max_value <= 0:
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
        tracking=True,
        default='draft',
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    description = fields.Text(
        string='Job Description',
        tracking=True,
    )
    name = fields.Char(
        string='Job Position',
        required=True,
        index=True,
        translate=True,
        tracking=True,
    )

    def request_approval(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_amend_system_users"):
            raise UserError(_('You do not have the permission to request '
                              'approval for this job position. '
                              'Please contact the support team.')
                            )
        return self.with_context(supplier_action=True).write({'state': 'waiting'})

    def action_approve(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_approve_system_users"):
            raise UserError(_('You do not have the permission to approve '
                              'this job position. '
                              'Please contact the support team.'
                              )
                            )
        return self.with_context(supplier_action=True).write(
            {'state': 'approved'}
        )

    def action_reject(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_approve_system_users"):
            raise UserError(_('You do not have the permission to reject '
                              'this job position. '
                              'Please contact the support team.')
                            )
        return self.with_context(supplier_action=True).write(
            {'state': 'rejected'}
        )

    def set_to_draft(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_amend_system_users"):
            raise UserError(_('You do not have the permission to make changes '
                              'to this job position. '
                              'Please contact the support team.')
                            )
        return self.with_context(supplier_action=True).write({'state': 'draft'})

    def write(self, vals):
        if self._context.get('supplier_action'):
            return super(HrJob, self.with_context(
                supplier_action=True)).write(vals)
        elif self.env.user.has_group(
                "approval_hierarchy.group_amend_system_users"):
            vals['state'] = 'draft'
            if 'job_role_ids' in vals:
                for job_role in vals.get('job_role_ids'):
                    if isinstance(job_role, list) and len(job_role) == 3 \
                            and isinstance(job_role[2], dict) and job_role[2] \
                            and isinstance(job_role[1], int):
                        role = self.env['hr.job.role'].browse(job_role[1])
                        message = "Changes made to the job role '{}'.".format(
                            role.name)
                        if 'permission' in job_role[2]:
                            message += '\nPermission: {}'.format(
                                job_role[2]['permission'])
                        if 'min_value' in job_role[2]:
                            message += '\nMin Value: {}'.format(
                                job_role[2]['min_value'])
                        if 'max_value' in job_role[2]:
                            message += '\nMax Value: {}'.format(
                                job_role[2]['max_value'])
                        self.message_post(body=message)
            return super(HrJob, self.with_context(
                supplier_action=True)).write(vals)
        else:
            raise UserError(_('You do not have the permission to make changes '
                              'to this job position. '
                              'Please contact the support team.')
                            )
