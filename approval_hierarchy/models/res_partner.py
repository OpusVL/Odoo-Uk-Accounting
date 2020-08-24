# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("waiting", "Waiting Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        tracking=True,
    )
    approval_user_id = fields.Many2one(
        'res.users',
        string='Approved by',
        tracking=True,
    )
    current_user = fields.Boolean(compute='_get_current_user')

    def _get_current_user(self):
        for rec in self:
            rec.current_user = rec.approval_user_id == self.env.user and True or False

    def request_approval(self):
        role_action = self.env.ref('approval_hierarchy.supplier_approval_role')
        approved_user = self.env.user.employee_id and \
                        self.env.user.employee_id.get_approved_user(
                            role_action) or False
        if approved_user == self.env.user:
            self.with_context(supplier_action=True).write(
                {'state': 'waiting', 'approval_user_id': approved_user.id}
            )
            self.action_approve()
        else:
            return self.with_context(supplier_action=True).write(
                {
                    'state': 'waiting',
                    'approval_user_id': approved_user and approved_user.id,
                }
            )

    def action_approve(self):
        return self.with_context(supplier_action=True).write(
            {'state': 'approved'}
        )

    def action_reject(self):
        return self.with_context(supplier_action=True).write(
            {'state': 'rejected'}
        )

    def action_reject2(self):
        return self.with_context(supplier_action=True).write(
            {'state': 'rejected'}
        )

    def set_to_draft(self):
        return self.with_context(supplier_action=True).write(
            {'state': 'draft'}
        )

