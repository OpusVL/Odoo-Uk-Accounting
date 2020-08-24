# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResUsers(models.Model):
    _inherit = 'res.users'

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
    has_delegated = fields.Boolean(compute='_check_has_delegated')

    def _check_has_delegated(self):
        for rec in self:
            rec.has_delegated = rec.delegated_user_id and True or False

    @api.depends('employee_ids.job_id')
    def _get_hr_job(self):
        for user in self:
            user.job_id = user.employee_id.job_id

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

