# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime


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
        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move' or not rec.get(
                'partner_id'):
            rec.update({
                'payment_date': payment_date,
            })
            return rec
        partner = self.env['res.partner'].browse(rec.get(
                'partner_id'))
        # If partner has no warning, check its company
        if partner.payment_warn == 'no-message' and partner.parent_id:
            partner = partner.parent_id
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
        if self._context.get('active_model') and self._context.get('active_ids'):
            return {}
        warning = {}
        title = False
        message = False

        partner = self.partner_id

        # If partner has no warning, check its company
        if partner.payment_warn == 'no-message' and partner.parent_id:
            partner = partner.parent_id
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
                self.update({'partner_id': False})
            return {'warning': warning}
        return {}

    @api.onchange('payment_date')
    def onchange_payment_date_warning(self):
        if not self.payment_date or not self.payment_date or not \
                self.register_payment_action or not self.env.user.has_group(
                    'approval_hierarchy.group_warning_payment'):
            return {}
        partner = self.partner_id

        # If partner has no warning, check its company
        if partner.payment_warn == 'no-message' and partner.parent_id:
            partner = partner.parent_id
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

