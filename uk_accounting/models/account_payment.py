# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    combined = fields.Boolean("Combined Invoices/Bills")

    @api.model
    def default_get(self, fields):
        """
        # Override base default_get without super because on base default is
        # raising error if inbound and out bound register payments at the same time
        # I added check_combined_configuration ,
        # if is activated on settings will not raise error
        :param fields:
        :return:
        """
        defaults = {}
        active_ids = self._context.get('active_ids')
        if not active_ids:
            return defaults
        invoices = self.env['account.move'].browse(active_ids)
        combined = False

        # Check all invoices are open
        if any(
                invoice.state != 'posted' or invoice.invoice_payment_state != 'not_paid' or not invoice.is_invoice()
                for invoice in invoices):
            raise UserError(
                _("You can only register payments for open invoices"))
        # Check all invoices are inbound or all invoices are outbound
        outbound_list = [invoice.is_outbound() for invoice in invoices]
        first_outbound = invoices[0].is_outbound()
        if any(x != first_outbound for x in outbound_list):
            if not self.check_combined_configuration():
                raise UserError(_(
                    "You can only register at the same time for payment that are all inbound or all outbound"))
            combined = True
            defaults['combined'] = combined
        if any(inv.company_id != invoices[0].company_id for inv in invoices):
            raise UserError(_(
                "You can only register at the same time for payment that are all from the same company"))
        if 'invoice_ids' not in defaults:
            defaults['invoice_ids'] = [(6, 0, invoices.ids)]
        if 'journal_id' not in defaults:
            defaults['journal_id'] = self.env['account.journal'].search(
                [('company_id', '=', self.env.company.id),
                 ('type', 'in', ('bank', 'cash'))], limit=1).id
        if 'payment_method_id' not in defaults:
            if not combined:
                if invoices[0].is_inbound():
                    domain = [('payment_type', '=', 'inbound')]
                else:
                    domain = [('payment_type', '=', 'outbound')]
                defaults['payment_method_id'] = self.env[
                    'account.payment.method'].search(domain, limit=1).id
            else:
                domain = [('payment_type', '=', 'combined')]
                defaults['payment_method_id'] = self.env[
                    'account.payment.method'].search(domain, limit=1).id
        return defaults
    
    def check_combined_configuration(self):
        return self.env.user.company_id.combined_payment

    @api.onchange('journal_id', 'invoice_ids')
    def _onchange_journal(self):
        res = super(AccountPaymentRegister, self)._onchange_journal()
        if self.combined:
            domain_payment = [('payment_type', '=', 'combined'), (
                'id', 'in', self.journal_id.combined_payment_method_ids.ids)]
            res.update({
                'domain': {'payment_method_id': domain_payment}
            })
        return res


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    payment_type = fields.Selection(selection_add=[("combined", "Combined")])
