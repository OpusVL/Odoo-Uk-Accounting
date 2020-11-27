# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.account.models.account_payment import MAP_INVOICE_TYPE_PARTNER_TYPE


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends('move_line_ids.matched_debit_ids',
                 'move_line_ids.matched_credit_ids')
    def _compute_reconciled_invoice_ids(self):
        '''
        Override base computed function to add more invoices linked to the
        payment. This was spotted when creating combined payment some of
        incoices were not linked to the payment.
        The change from original function is on calculating reconciled_moves
        '''
        for record in self:
            # Change from original function starts here
            partial_reconciled_moves = record.move_line_ids.mapped(
                'matched_debit_ids.debit_move_id.move_id.id') \
                               + record.move_line_ids.mapped(
                'matched_credit_ids.credit_move_id.move_id.id')
            full_reconciled_moves = record.move_line_ids.mapped(
                'full_reconcile_id.partial_reconcile_ids.debit_move_id.move_id.id') + \
                                    record.move_line_ids.mapped(
                                        'full_reconcile_id.partial_reconcile_ids.credit_move_id.move_id.id')
            reconciled_move_ids = list(
                set(partial_reconciled_moves + full_reconciled_moves)
            )
            reconciled_moves = self.env['account.move'].browse(
                reconciled_move_ids)
            # Change end here
            record.reconciled_invoice_ids = reconciled_moves.filtered(
                lambda move: move.is_invoice())
            record.has_invoices = bool(record.reconciled_invoice_ids)
            record.reconciled_invoices_count = len(
                record.reconciled_invoice_ids)

    @api.model
    def default_get(self, default_fields):
        if not self.env.user.company_id.combined_payment:
            return super(AccountPayment, self).default_get(default_fields)
        else:
            active_ids = self._context.get('active_ids') or self._context.get(
                'active_id')
            active_model = self._context.get('active_model')
            # Calling super with context active_ids = False to call super
            # but to skip the error if invoices are of different types
            res = super(AccountPayment, self.with_context(
                active_ids=False)).default_get(default_fields)

            # After skipping the check on base default_get, added the
            # same lines without the check of invoice types
            invoices = self.env['account.move'].browse(active_ids).filtered(
                lambda move: move.is_invoice(include_receipts=True))
            # Check for selected invoices ids
            if not active_ids or active_model != 'account.move':
                return res

            # Check all invoices are open
            if not invoices or any(
                    invoice.state != 'posted' for invoice in invoices):
                raise UserError(
                    _("You can only register payments for open invoices"))

            amount = self._compute_payment_amount(
                invoices,
                invoices[0].currency_id,
                invoices[0].journal_id, res.get(
                    'payment_date') or fields.Date.today()
            )
            res.update({
                'currency_id': invoices[0].currency_id.id,
                'amount': abs(amount),
                'payment_type': 'inbound' if amount > 0 else 'outbound',
                'partner_id': invoices[0].commercial_partner_id.id,
                'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].type],
                'communication': invoices[0].invoice_payment_ref or invoices[
                    0].ref or invoices[0].name,
                'invoice_ids': [(6, 0, invoices.ids)],
            })
            return res


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    combined = fields.Boolean("Combined Invoices/Bills")

    @api.model
    def default_get(self, fields):
        """
        Override base default_get without super because on base default is
        raising error if inbound and out bound register payments at the same time
        I added check_combined_configuration ,
        if is activated on settings will not raise error
        :param fields:
        :return: defaults: dict() of fieldnames and values
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
