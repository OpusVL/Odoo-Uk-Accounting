# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model_create_multi
    def create(self, vals_list):
        moves = super(AccountMove, self).create(vals_list)
        for move in moves:
            if move.type == 'out_invoice':
                # Check Input AR Invoice access rights
                move.with_context(approval_origin='create'
                                  )._check_customer_invoice_access_rights()
            elif move.type == 'in_invoice':
                # Check Input AP Invoice access rights
                move.with_context(approval_origin='create')._check_vendor_bill_access_rights()
        return moves

    def write(self, vals):
        if self._context.get('supplier_action'):
            return super(AccountMove, self.with_context(
                supplier_action=True)).write(vals)
        for move in self:
            if 'type' not in vals and move.type == 'out_invoice':
                # Check Input AR Invoice access rights
                move.with_context(approval_origin='write'
                                  )._check_customer_invoice_access_rights()
            elif 'type' not in vals and move.type == 'in_invoice':
                # Check Input AP Invoice access rights
                move.with_context(approval_origin='write'
                                  )._check_vendor_bill_access_rights()
            elif 'type' in vals and vals.get('type') == 'out_invoice':
                # Check Input AR Invoice access rights
                move.with_context(approval_origin='write'
                                  )._check_customer_invoice_access_rights()
            elif 'type' in vals and vals.get('type') == 'in_invoice':
                # Check Input AP Invoice access rights
                move.with_context(approval_origin='write'
                                  )._check_vendor_bill_access_rights()
        return super(AccountMove, self.with_context(
                supplier_action=True)).write(vals)

    def unlink(self):
        for move in self:
            if move.type == 'out_invoice':
                # Check Input AR Invoice access rights
                move.with_context(approval_origin='unlink'
                                  )._check_customer_invoice_access_rights()
            elif move.type == 'in_invoice':
                # Check Input AP Invoice access rights
                move.with_context(approval_origin='unlink'
                                  )._check_vendor_bill_access_rights()
        return super(AccountMove, self).unlink()

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
