# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError
from odoo.addons.approval_hierarchy.helpers import CUSTOM_ERROR_MESSAGES


def _get_warn_partner_id(partner):
    # If partner has no warning, check its company
    if partner.payment_warn != 'block' and partner.parent_id and \
            partner.parent_id.payment_warn == 'block':
        partner = partner.parent_id
    return partner


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # Override the field cause i needed to remove the default,
    # and to input the default value in default_get
    payment_date = fields.Date(
        string='Date',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
    )
    register_payment_action = fields.Boolean()

    @api.model
    def default_get(self, default_fields):
        rec = super(AccountPayment, self).default_get(default_fields)
        payment_date = datetime.now()
        if rec.get('partner_id'):
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

    def export_data(self, fields_to_export):
        """ Override to check if user has rights to export """
        if not self.env.user.has_group(
                "approval_hierarchy.export_payment_run_role"):
            raise UserError(
                CUSTOM_ERROR_MESSAGES.get('export') % 'payments')
        return super(AccountPayment, self).export_data(fields_to_export)

    def post(self):
        payments = self.filtered(lambda payment: payment.partner_id)
        return super(AccountPayment, payments).post()


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
