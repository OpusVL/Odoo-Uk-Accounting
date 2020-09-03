# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.approval_hierarchy.helpers import CONFIGURATION_ERROR_MESSAGE, CUSTOM_ERROR_MESSAGES
from odoo.api import SUPERUSER_ID


class AccountMove(models.Model):
    _inherit = "account.move"

    state = fields.Selection(
        selection_add=[
            ('waiting', 'Waiting'),
        ],
    )
    approval_user_id = fields.Many2one(
        'res.users',
        string='Approved by',
        tracking=True,
    )
    current_user = fields.Boolean(compute='_get_current_user')

    def _get_current_user(self):
        for rec in self:
            rec.current_user = rec.approval_user_id == self.env.user

    @api.model_create_multi
    def create(self, vals_list):
        moves = super(AccountMove, self).create(vals_list)
        for move in moves:
            move.with_context(approval_origin='create'
                              ).check_move_approval_access_rights()
        return moves

    def write(self, vals):
        if self._context.get('supplier_action'):
            return super(AccountMove, self.with_context(
                supplier_action=True)).write(vals)
        for move in self:
            move.with_context(approval_origin='write'
                              ).check_move_approval_access_rights()
        return super(AccountMove, self.with_context(
                supplier_action=True)).write(vals)

    def unlink(self):
        for move in self:
            move.with_context(approval_origin='unlink'
                              ).check_move_approval_access_rights()
        return super(AccountMove, self).unlink()

    def check_move_approval_access_rights(self):
        if self.env.user.id == SUPERUSER_ID:
            return True
        approval_access_dict = {
            'out_invoice': '_check_customer_invoice_access_rights',
            'out_refund': '_check_customer_invoice_access_rights',
            'in_invoice': '_check_vendor_bill_access_rights',
            'in_refund': '_check_vendor_bill_access_rights',
            'entry': '_check_account_move_access_rights',
            'out_receipt': '_check_customer_invoice_access_rights',
            'in_receipt': '_check_vendor_bill_access_rights',
        }
        getattr(self.with_context(approval_origin=self._context.get(
            'approval_origin')), approval_access_dict.get(self.type))()
        return True

    def _check_customer_invoice_access_rights(self):
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(CONFIGURATION_ERROR_MESSAGE)
        role_action = self.env.ref(
            'approval_hierarchy.input_ar_invoice_role')
        if not self.env.user.employee_id.check_if_has_approval_rights(
                role_action):
            raise UserError(CUSTOM_ERROR_MESSAGES.get(self._context.get(
                'approval_origin')) % 'customer invoice')
        return True

    def _check_vendor_bill_access_rights(self):
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(CONFIGURATION_ERROR_MESSAGE)
        role_action = self.env.ref(
            'approval_hierarchy.input_ap_invoice_role')
        if not self.env.user.employee_id.check_if_has_approval_rights(
                role_action):
            raise UserError(CUSTOM_ERROR_MESSAGES.get(self._context.get(
                'approval_origin')) % 'vendor bill')
        return True

    def _check_account_move_access_rights(self):
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(CONFIGURATION_ERROR_MESSAGE)
        role_action = self.env.ref(
            'approval_hierarchy.input_account_move_role')
        if not self.env.user.employee_id.check_if_has_approval_rights(
                role_action):
            raise UserError(CUSTOM_ERROR_MESSAGES.get(self._context.get(
                'approval_origin')) % 'journal entry')
        return True

    def request_approval(self):
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(CONFIGURATION_ERROR_MESSAGE)
        amend_role_action = False
        if self.type in ('out_invoice', 'out_refund'):
            amend_role_action = self.env.ref(
                'approval_hierarchy.input_ar_invoice_role')
        elif self.type in ('in_invoice', 'in_refund'):
            amend_role_action = self.env.ref(
                'approval_hierarchy.input_ap_invoice_role')
        elif self.type == 'entry':
            amend_role_action = self.env.ref(
                'approval_hierarchy.input_account_move_role')
        if not self.env.user.employee_id.check_if_has_approval_rights(
                amend_role_action):
            raise UserError(CUSTOM_ERROR_MESSAGES.get('request'))
        approval_role_action = self.get_approval_role_action()
        approved_user = self.env.user.employee_id.get_approved_user(
            approval_role_action, self.amount_total, self.currency_id)
        if approved_user == self.env.user:
            self.with_context(supplier_action=True).write(
                {
                    'state': 'waiting',
                    'approval_user_id': approved_user.id,
                }
            )
            self.action_post()
        else:
            return self.with_context(supplier_action=True).write(
                {
                    'state': 'waiting',
                    'approval_user_id': approved_user and approved_user.id,
                }
            )

    def action_post(self):
        # Double check in code if the user that
        # is approving has rights to approve
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(CONFIGURATION_ERROR_MESSAGE)
        role_action = self.get_approval_role_action()
        if not self.env.user.employee_id.check_if_has_approval_rights(
                role_action, self.amount_total, self.currency_id):
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('approve') % 'a journal entry')
        return super(AccountMove, self.with_context(
                supplier_action=True)).action_post()

    def action_reject(self):
        # Double check in code if the user that
        # is rejecting has rights to reject
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(CONFIGURATION_ERROR_MESSAGE)
        role_action = self.get_approval_role_action()
        if not self.env.user.employee_id.check_if_has_approval_rights(
                role_action, self.amount_total, self.currency_id):
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('reject') % 'a journal entry')
        return self.with_context(supplier_action=True).write(
            {'state': 'cancel'}
        )

    def get_approval_role_action(self):
        role_action_dict = {
            'out_invoice': 'approval_hierarchy.approve_ar_invoice_role',
            'in_invoice': 'approval_hierarchy.approve_ap_invoice_role',
            'out_refund': 'approval_hierarchy.approve_ar_credit_note_role',
            'in_refund': 'approval_hierarchy.approve_ap_credit_memo_role',
            'entry': 'approval_hierarchy.post_journal_role',
            'out_receipt': 'approval_hierarchy.approve_ar_invoice_role',
            'in_receipt': 'approval_hierarchy.approve_ap_invoice_role'
        }
        return self.env.ref(role_action_dict.get(self.type))
