# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


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
            move.check_move_approval_access_rights()
        return moves

    def write(self, vals):
        if self._context.get('supplier_action'):
            return super(AccountMove, self.with_context(
                supplier_action=True)).write(vals)
        for move in self:
            move.check_move_approval_access_rights()
        return super(AccountMove, self.with_context(
                supplier_action=True)).write(vals)

    def unlink(self):
        for move in self:
            move.check_move_approval_access_rights()
        return super(AccountMove, self).unlink()

    def check_move_approval_access_rights(self):
        if self.type in ('out_invoice', 'out_refund'):
            # Check Input C Invoice access rights
            self.with_context(approval_origin='unlink'
                              )._check_customer_invoice_access_rights()
        elif self.type in ('in_invoice', 'in_refund'):
            # Check Input AP Invoice access rights
            self.with_context(approval_origin='unlink'
                              )._check_vendor_bill_access_rights()
        else:
            self.with_context(approval_origin='write'
                              )._check_account_move_access_rights()
        return True

    def _check_customer_invoice_access_rights(self):
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(_('Your user account is not configured '
                              'properly. '
                              'Please contact the support team.'))
        role_action = self.env.ref(
            'approval_hierarchy.input_ar_invoice_role')
        if not self.env.user.employee_id.check_if_has_approval_rights(
                role_action):
            custom_error_messages = {
                'create': _('You do not have the permission to create a '
                            'customer invoice. Please contact the support team.'
                            ),
                'write': _('You do not have the permission to modify a '
                           'customer invoice. Please contact the support team.'
                           ),
                'unlink': _('You do not have the permission to delete a '
                            'customer invoice. Please contact the support team.'
                            ),
            }
            raise UserError(custom_error_messages.get(self._context.get(
                'approval_origin')))
        return True

    def _check_vendor_bill_access_rights(self):
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(_('Your user account is not configured '
                              'properly. '
                              'Please contact the support team.'))
        role_action = self.env.ref(
            'approval_hierarchy.input_ap_invoice_role')
        if not self.env.user.employee_id.check_if_has_approval_rights(
                role_action):
            custom_error_messages = {
                'create': _('You do not have the permission to create a vendor '
                            'bill. Please contact the support team.'),
                'write': _('You do not have the permission to modify a vendor '
                           'bill. Please contact the support team.'),
                'unlink': _('You do not have the permission to modify a vendor '
                            'bill. Please contact the support team.'),
            }
            raise UserError(custom_error_messages.get(self._context.get(
                'approval_origin')))
        return True

    def _check_account_move_access_rights(self):
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(_('Your user account is not configured '
                              'properly. '
                              'Please contact the support team.'))
        role_action = self.env.ref(
            'approval_hierarchy.input_account_move_role')
        if not self.env.user.employee_id.check_if_has_approval_rights(
                role_action):
            custom_error_messages = {
                'create': _('You do not have the permission to create a '
                            'journal. Please contact the support team.'
                            ),
                'write': _('You do not have the permission to modify a '
                           'journal. Please contact the support team.'
                           ),
                'unlink': _('You do not have the permission to delete a '
                            'journal. Please contact the support team.'
                            ),
            }
            raise UserError(custom_error_messages.get(self._context.get(
                'approval_origin')))
        return True

    def request_approval(self):
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(_('Your user account is not configured properly. '
                              'Please contact the support team.'))
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
        if amend_role_action and not self.env.user.employee_id.check_if_has_approval_rights(
                amend_role_action):
            raise UserError(_('You do not have the permission to request '
                              'approval. Please contact the support team.'))
        approval_role_action = self.get_approval_role_action()
        approved_user = self.env.user.employee_id.get_approved_user_amount_interval(
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
            raise UserError(_('Your user account is not configured properly. '
                              'Please contact the support team.'))
        role_action = self.get_approval_role_action()
        if not self.env.user.employee_id.check_if_has_approval_rights_amount_interval(
                role_action, self.amount_total, self.currency_id):
            raise UserError(_('You do not have the permission to approve this '
                              'record. Please contact the support team.'))
        return super(AccountMove, self.with_context(
                supplier_action=True)).action_post()

    def action_reject(self):
        # Double check in code if the user that
        # is rejecting has rights to reject
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(_('Your user account is not configured properly. '
                              'Please contact the support team.'))
        role_action = self.get_approval_role_action()
        if not self.env.user.employee_id.check_if_has_approval_rights_amount_interval(
                role_action, self.amount_total, self.currency_id):
            raise UserError(_('You do not have the permission to reject this '
                              'record. Please contact the support team.'))
        return self.with_context(supplier_action=True).write(
            {'state': 'cancel'}
        )

    def get_approval_role_action(self):
        role_action = False
        if self.type == 'out_invoice':
            role_action = self.env.ref(
                'approval_hierarchy.approve_ar_invoice_role')
        elif self.type == 'in_invoice':
            role_action = self.env.ref(
                'approval_hierarchy.approve_ap_invoice_role')
        elif self.type == 'out_refund':
            role_action = self.env.ref(
                'approval_hierarchy.approve_ar_credit_note_role')
        elif self.type == 'in_refund':
            role_action = self.env.ref(
                'approval_hierarchy.approve_ap_credit_note_role')
        elif self.type == 'entry':
            role_action = self.env.ref(
                'approval_hierarchy.post_journal_role')
        return role_action
