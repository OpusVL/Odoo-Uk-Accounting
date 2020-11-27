# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _default_combined_payment_methods(self):
        return self.env.ref(
            'uk_accounting.account_payment_method_manual_combined')

    show_combined_payment = fields.Boolean(
        string='Show Combined Payment',
        related='company_id.combined_payment',
        readonly=True)
    combined_payment_method_ids = fields.Many2many(
        'account.payment.method',
        'account_journal_combined_payment_method_rel',
        'journal_id',
        'combined_payment_method',
        domain=[('payment_type', '=', 'combined')],
        string='For Combined Payments',
        default=lambda self: self._default_combined_payment_methods(),
        help="Manual:Pay bill by cash or any other method outside of Odoo.\n" 
             "Check:Pay bill by check and print it from Odoo.\n"
             "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file "
             "you submit to your bank. Enable this option from the settings.")
