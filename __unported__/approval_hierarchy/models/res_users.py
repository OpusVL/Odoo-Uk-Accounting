# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.api import SUPERUSER_ID


class ResUsers(models.Model):
    _name = 'res.users'
    _inherit = ['res.users', 'mail.thread', 'mail.activity.mixin']

    delegated_user_id = fields.Many2one(
        related='employee_id.delegated_user_id',
        readonly=False,
        related_sudo=False,
    )
    job_id = fields.Many2one(
        'hr.job',
        compute='_get_hr_job',
        store=True,
    )
    manager_user_id = fields.Many2one(
        'res.users',
        compute='_get_managers',
        store=True,
    )
    manager_employee_id = fields.Many2one(
        'hr.employee',
        compute='_get_managers',
        store=True,
    )
    has_delegated = fields.Boolean(compute='_check_has_delegated')
    current_user = fields.Boolean(compute='_compute_current_user')

    def _compute_current_user(self):
        for user in self:
            user.current_user = user == self.env.user

    def is_superuser(self):
        self.ensure_one()
        # TODO, we have to revert second or control
        #  after fixing the superuser problem
        if self.id == SUPERUSER_ID or self.login == 'admin':
            return True
        else:
            return False

    def _check_has_delegated(self):
        for rec in self:
            rec.has_delegated = bool(rec.delegated_user_id)

    @api.depends('employee_ids.job_id')
    def _get_hr_job(self):
        for user in self:
            user.job_id = user.employee_id.job_id

    @api.depends('employee_ids.parent_id')
    def _get_managers(self):
        for user in self:
            user.manager_user_id = user.employee_id.parent_id and \
                             user.employee_id.parent_id.user_id.id or False
            user.manager_employee_id = user.employee_id.parent_id.id

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights.
            Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        hr_readable_fields = [
            'job_id',
            'delegated_user_id',
        ]

        hr_writable_fields = [
            'delegated_user_id',
            'job_id',
        ]

        init_res = super(ResUsers, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = type(self).SELF_READABLE_FIELDS + hr_readable_fields + hr_writable_fields
        type(self).SELF_WRITEABLE_FIELDS = type(self).SELF_WRITEABLE_FIELDS + hr_writable_fields
        return init_res


class Groups(models.Model):
    _inherit = "res.groups"

    enable_value = fields.Boolean(string='Enable Limit Value', )
    approval_group = fields.Boolean(string='Approval Group', )

    def _get_hidden_extra_categories(self):
        result = super(Groups, self)._get_hidden_extra_categories()
        result.append(
            'approval_hierarchy.module_category_approval_hierarchy'
        )
        return result
