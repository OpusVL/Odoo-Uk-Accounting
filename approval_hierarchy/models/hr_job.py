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
    state = fields.Selection([
        ('draft', 'Draft'),
        ('recruit', 'Recruitment in Progress'),
        ('open', 'Not Recruiting'),
        ('waiting', 'Waiting'),
        ('rejected', 'Rejected'),
        ('approved', 'Approved')],
        string='Status',
        readonly=True,
        required=True,
        tracking=True,
        copy=False,
        default='draft',)
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
            raise UserError(_('You dont have the rights to request approval for'
                              ' this job position, Please contact with '
                              'an administrator.')
                            )
        return self.write({'state': 'waiting'})

    def action_approve(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_approve_system_users"):
            raise UserError(_('You dont have the rights to approve this job '
                              'position, Please contact with an administrator.')
                            )
        return self.with_context(supplier_action=True).write(
            {'state': 'approved'}
        )

    def action_reject(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_approve_system_users"):
            raise UserError(_('You dont have the rights to reject this job '
                              'position, Please contact with an administrator.')
                            )
        return self.with_context(supplier_action=True).write(
            {'state': 'rejected'}
        )

    def set_to_draft(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_amend_system_users"):
            raise UserError(_('You dont have the rights to send to draft'
                              ' this job position, Please contact with '
                              'an administrator.')
                            )
        return self.write({'state': 'draft'})

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
                            and isinstance(job_role[2], dict) and job_role[2]:
                        role = self.env['hr.job.role'].browse(job_role[1])
                        message = "Job role {} has been modified.".format(
                            role.name)
                        self.message_post(body=message)
            return super(HrJob, self.with_context(
                supplier_action=True)).write(vals)
        else:
            raise UserError(_('You dont have the rights to modify a job '
                              'position, Please contact with an administrator.')
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
