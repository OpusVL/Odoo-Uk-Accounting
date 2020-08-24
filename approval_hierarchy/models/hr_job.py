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
                    "Min Value must be equal or smaller than max value."))

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

