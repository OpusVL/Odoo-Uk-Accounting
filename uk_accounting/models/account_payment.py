from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends("move_line_ids.matched_debit_ids", "move_line_ids.matched_credit_ids")
    def _compute_reconciled_invoice_ids(self):
        """
        Override base computed function to add more invoices linked to the
        payment. This was spotted when creating combined payment some of
        incoices were not linked to the payment.
        The change from original function is on calculating reconciled_moves
        """
        for record in self:
            # Change from original function starts here
            mls = record.move_line_ids
            mls_debit_moves = mls.mapped("matched_debit_ids.debit_move_id.move_id")
            mls_credit_moves = mls.mapped("matched_credit_ids.credit_move_id.move_id")
            mls_debit_reconciles = mls.mapped(
                "full_reconcile_id.partial_reconcile_ids.debit_move_id.move_id"
            )
            mls_credit_reconciles = mls.mapped(
                "full_reconcile_id.partial_reconcile_ids.credit_move_id.move_id"
            )
            reconciled_moves = (
                mls_debit_moves
                | mls_credit_moves
                | mls_debit_reconciles
                | mls_credit_reconciles
            )
            # Change end here
            record.reconciled_invoice_ids = reconciled_moves.filtered(
                lambda move: move.is_invoice()
            )
            record.has_invoices = bool(record.reconciled_invoice_ids)
            record.reconciled_invoices_count = len(record.reconciled_invoice_ids)


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    combined = fields.Boolean("Combined Invoices/Bills")

    def check_combined_configuration(self):
        return self.env.user.company_id.combined_payment

    @api.onchange("journal_id", "invoice_ids")
    def _onchange_journal(self):
        res = super(AccountPaymentRegister, self)._onchange_journal()
        if self.combined:
            domain_payment = [
                ("payment_type", "=", "combined"),
                ("id", "in", self.journal_id.combined_payment_method_ids.ids),
            ]
            res.update({"domain": {"payment_method_id": domain_payment}})
        return res


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    payment_type = fields.Selection(
        ondelete={
            "combined": "cascade",
        },
        selection_add=[("combined", "Combined")],
    )
