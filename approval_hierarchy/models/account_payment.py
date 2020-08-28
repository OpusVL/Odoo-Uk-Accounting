# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime


def _get_warn_partner_id(partner):
    # If partner has no warning, check its company
    if partner.payment_warn != 'block' and partner.parent_id and \
            partner.parent_id.payment_warn == 'block':
        partner = partner.parent_id
    return partner


class AccountPayment(models.Model):
    _inherit = "account.payment"

    payment_date = fields.Date(
        string='Date',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
        tracking=True,
    )
    register_payment_action = fields.Boolean()

    @api.model
    def default_get(self, default_fields):
        rec = super(AccountPayment, self).default_get(default_fields)
        payment_date = datetime.now()
        active_ids = self._context.get('active_ids') or self._context.get(
            'active_id')
        active_model = self._context.get('active_model')
        if not active_ids or active_model != 'account.move' or not rec.get(
                'partner_id'):
            rec.update({
                'payment_date': payment_date,
            })
            return rec
        partner = self.env['res.partner'].browse(rec.get(
                'partner_id'))
        partner = _get_warn_partner_id(partner)
        if partner.payment_warn and partner.payment_warn != 'no-message':
            payment_date = False
        rec.update({
            'register_payment_action': True,
            'payment_date': payment_date,
        })
        return rec

    @api.onchange('partner_id')
    def onchange_partner_id_warning(self):
        if not self.partner_id or not self.env.user.has_group(
                'approval_hierarchy.group_warning_payment'):
            return {}
        if self._context.get('active_model') and self._context.get(
                'active_ids') and \
                self._context.get('active_model') != 'account.payment.register':
            return {}
        warning = {}
        title = False
        message = False

        partner = self.partner_id

        # If partner has no warning, check its company
        if partner.payment_warn == 'no-message' and partner.parent_id:
            partner = partner.parent_id
        if partner.payment_warn and partner.payment_warn != 'no-message':
            partner = _get_warn_partner_id(partner)
            title = _("Warning for %s") % partner.name
            message = partner.payment_warn_msg
            warning = {
                'title': title,
                'message': message
            }
            if partner.payment_warn == 'block':
                self.update({'partner_id': False})
            return {'warning': warning}
        return {}

    @api.onchange('payment_date')
    def onchange_payment_date_warning(self):
        if not self.payment_date or not self.partner_id or not \
                self.register_payment_action or not self.env.user.has_group(
                    'approval_hierarchy.group_warning_payment'):
            return {}
        partner = self.partner_id
        partner = _get_warn_partner_id(partner)
        if partner.payment_warn and partner.payment_warn != 'no-message':
            # Block if partner only has warning but parent company is blocked
            if partner.payment_warn != 'block' and partner.parent_id and partner.parent_id.payment_warn == 'block':
                partner = partner.parent_id
            title = _("Warning for %s") % partner.name
            message = partner.payment_warn_msg
            warning = {
                'title': title,
                'message': message
            }
            if partner.payment_warn == 'block':
                self.update({'payment_date': False})
            return {'warning': warning}
        return {}


class PaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _prepare_payment_vals(self, invoices):
        payment_vals = super(PaymentRegister, self)._prepare_payment_vals(
            invoices)
        partner = invoices[0].commercial_partner_id
        partner = _get_warn_partner_id(partner)
        if partner.payment_warn and partner.payment_warn != 'no-message':
            payment_vals.update({'partner_id': False})
        return payment_vals

    # Override function to post only the payments that has filled the partner
    def create_payments(self):
        '''Create payments according to the invoices.
        Having invoices with different commercial_partner_id or different type
        (Vendor bills with customer invoices) leads to multiple payments.
        In case of all the invoices are related to the same
        commercial_partner_id and have the same type, only one payment will be
        created.

        :return: The ir.actions.act_window to show created payments.
        '''
        Payment = self.env['account.payment']
        payments = Payment.create(self.get_payments_vals())
        payments.filtered(lambda payment: payment.partner_id).post()

        action_vals = {
            'name': _('Payments'),
            'domain': [('id', 'in', payments.ids)],
            'res_model': 'account.payment',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
        if len(payments) == 1:
            action_vals.update({'res_id': payments[0].id, 'view_mode': 'form'})
        else:
            action_vals['view_mode'] = 'tree,form'
        return action_vals
