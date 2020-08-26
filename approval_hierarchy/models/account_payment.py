# -*- coding: utf-8 -*-

from odoo import models, api, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.onchange('partner_id')
    def onchange_partner_id_warning(self):
        if not self.partner_id or not self.env.user.has_group(
                'approval_hierarchy.group_warning_payment'):
            return
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

