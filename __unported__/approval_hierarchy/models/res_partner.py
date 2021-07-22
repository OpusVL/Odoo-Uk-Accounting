# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.addons.approval_hierarchy import helpers
from odoo.addons.approval_hierarchy.helpers import CONFIGURATION_ERROR_MESSAGE, CUSTOM_ERROR_MESSAGES


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _default_category(self):
        return self.env['res.partner.category'].browse(
            self._context.get('category_id'))

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("waiting", "Awaiting Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
    )
    approval_user_id = fields.Many2one(
        'res.users',
        string='Approver',
    )
    current_user = fields.Boolean(compute='_get_current_user')
    payment_warn = fields.Selection(
        WARNING_MESSAGE,
        'Payment',
        help=WARNING_HELP,
        default="no-message",
    )
    payment_warn_msg = fields.Text(
        'Message for Payment',
    )

    def _get_current_user(self):
        for rec in self:
            rec.current_user = rec.approval_user_id == self.env.user

    @api.depends('is_company')
    def _compute_company_type(self):
        for partner in self:
            partner.company_type = 'company' if partner.is_company else 'person'

    def _write_company_type(self):
        for partner in self:
            partner.is_company = partner.company_type == 'company'

    def request_approval(self):
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(CONFIGURATION_ERROR_MESSAGE)
        amend_role_action = self.env.ref(
            'approval_hierarchy.supplier_set_up_role')
        if not self.env.user.employee_id.check_if_has_approval_rights(
                amend_role_action):
            raise UserError(CUSTOM_ERROR_MESSAGES.get('request'))
        approval_role_action = self.env.ref(
            'approval_hierarchy.supplier_approval_role')
        approved_user = self.env.user.employee_id and \
                        self.env.user.employee_id.get_approved_user(
                            approval_role_action)
        if approved_user == self.env.user:
            records = self | self.child_ids.filtered(
                lambda child: child.state == 'draft')
            records.with_context(supplier_action=True).write(
                {
                    'state': 'waiting',
                    'approval_user_id': approved_user.id,
                }
            )
            self.action_approve()
        else:
            records = self | self.child_ids.filtered(
                lambda child: child.state == 'draft')
            records.with_context(supplier_action=True).write(
                {
                    'state': 'waiting',
                    'approval_user_id': approved_user and approved_user.id,
                }
            )
            return True

    def action_approve(self):
        # double validation, in fact buttons action_approve and action_reject
        # are visible only for a single user which has been filled when
        # requesting approval.
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(CONFIGURATION_ERROR_MESSAGE)
        role_action = self.env.ref(
            'approval_hierarchy.supplier_approval_role')
        if not self.env.user.employee_id.check_if_has_approval_rights(
                role_action):
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('approve') % 'a partner')
        records = self | self.child_ids.filtered(
            lambda child: child.state != 'done')
        records.with_context(supplier_action=True).write(
            {'state': 'approved'}
        )
        return True

    def action_reject(self):
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(CONFIGURATION_ERROR_MESSAGE)
        role_action = self.env.ref(
            'approval_hierarchy.supplier_approval_role')
        if not self.env.user.employee_id.check_if_has_approval_rights(
                role_action):
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('reject') % 'a partner')
        records = self | self.child_ids
        records.with_context(supplier_action=True).write(
            {'state': 'rejected'}
        )
        return True

    def action_approve_administrator(self):
        records = self | self.child_ids.filtered(
            lambda r: r.state != 'done'
        )
        records.with_context(supplier_action=True).write(
            {'state': 'approved'}
        )
        return True

    def action_reject_administrator(self):
        records = self | self.child_ids
        records.with_context(supplier_action=True).write(
            {'state': 'rejected'}
        )
        return True

    def set_to_draft(self):
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(CONFIGURATION_ERROR_MESSAGE)
        role_action = self.env.ref(
            'approval_hierarchy.supplier_set_up_role')
        if not self.env.user.employee_id.check_if_has_approval_rights(
                role_action):
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('write') % 'a partner')
        return self.with_context(supplier_action=True).write(
            {
                'state': 'draft',
                'approval_user_id': False,
             }
        )

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        if vals and vals.get('parent_id'):
            message = "Contact '{}' is created. ".format(
                res.name)
            res.parent_id.message_post(body=message)
        return res

    def write(self, vals):
        # I tried to transfer this hook on BaseModel but the record
        # state was not changing
        fields_to_be_tracked = helpers.get_fields_to_be_tracked()
        if fields_to_be_tracked.get(
                self._name) and any(field in vals for field in
                                    fields_to_be_tracked.get(self._name)) and \
                not self._context.get('supplier_action'):
            vals['state'] = 'draft'
        if 'child_ids' in vals:
            if len(vals) == 1:
                return super(ResPartner, self).write(vals)
            for child in vals.get('child_ids'):
                if isinstance(child, list) and len(child) == 3 \
                        and isinstance(child[2], dict) and child[2] and \
                        isinstance(child[1], int):
                    child[2].update({
                        'state': 'draft',
                        'approval_user_id': False,
                    })
                    message = "Changes made to the contact '{}'".format(
                        self.browse(child[1]).name)
                    self.message_post(body=message)
                vals['state'] = 'draft'
                vals['approval_user_id'] = False
        return super(ResPartner,  self).write(vals)

    def unlink(self):
        for partner in self:
            if partner.state != 'draft':
                raise UserError(_('In order to delete a partner, '
                                  'you must set it first to draft.'))
            if partner.parent_id:
                message = "Contact '{}' is deleted.".format(
                    partner.name)
                partner.parent_id.message_post(body=message)
                partner.parent_id.set_to_draft()
        return super(ResPartner, self).unlink()


class ResPartnerBank(models.Model):
    _name = 'res.partner.bank'
    _inherit = ['res.partner.bank', 'mail.thread', 'mail.activity.mixin']

    @api.model
    def create(self, vals):
        res = super(ResPartnerBank, self).create(vals)
        if vals:
            message = "Bank Account '{}' is created. " \
                      "View accounts detail for more information".format(
                res.acc_number)
            res.partner_id.message_post(body=message)
        return res

    def unlink(self):
        for bank_account in self:
            message = "Bank Account '{}' is deleted.".format(
                bank_account.acc_number)
            bank_account.partner_id.message_post(body=message)
        return super(ResPartnerBank, self).unlink()

    def write(self, vals):
        res = super(ResPartnerBank, self).write(vals)
        message = False
        if 'acc_number' in vals:
            message = "Changes made to the bank account '{}'." \
                      "View accounts detail for more information".format(
                vals.get('acc_number'))
        elif len(vals) != 1 and 'partner_id' not in vals:
            message = "Changes made to the bank account '{}'. " \
                      "View accounts detail for more information".format(
                self.acc_number)
        if message:
            self.partner_id.message_post(body=message)
        return res
