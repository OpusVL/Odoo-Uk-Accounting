from odoo import api, fields, models
from odoo.http import request


class AccountAccountType(models.Model):
    _inherit = "account.account.type"

    type = fields.Selection(selection_add=[("view", "View")])
    internal_group = fields.Selection(selection_add=[("view", "View")])


class AccountAccount(models.Model):
    _inherit = "account.account"

    parent_id = fields.Many2one(
        comodel_name="account.account", string="Parent Account", ondelete="set null"
    )


class AccountAccountTemplate(models.Model):
    _inherit = "account.account.template"

    parent_id = fields.Many2one(
        comodel_name="account.account.template",
        string="Parent Account",
        ondelete="set null",
    )


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def try_loading(self, company=False):
        """
        Method called from xml function to purge account.account records that
        were created when l10n_uk was installed. Follows the same logic as the
        base function without the check if an account.chart.template is already
        set on the company.

        Additionally calls a custom method to set the parent of an account
        once all the new account.account records have been created, based on the
        parent in the matching account.account.template record.
        :param company: <res.company>
        :return: None
        """
        if not company:
            if request and hasattr(request, "allowed_company_ids"):
                company = self.env["res.company"].browse(request.allowed_company_ids[0])
            else:
                company = self.env.company
        for template in self:
            template.with_context(default_company_id=company.id)._load(
                15.0, 15.0, company
            )
            self._set_account_parent()

    def _set_account_parent(self):
        """
        Sets the parent on every account.account record that has just been
        created, based on the corresponding parent defined in account.account.template
        :return: None
        """
        accounts = self.env["account.account"].search([])
        account_templates = self.env["account.account.template"].search([])
        for account in accounts:
            template = account_templates.filtered(
                lambda at: at.code and at.code.ljust(6, "0") == account.code
            )
            if template.parent_id:
                parent = accounts.filtered(
                    lambda a: a.code == template.parent_id.code.ljust(6, "0")
                )
                account.parent_id = parent


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # Inheriting base function to add the parent_id in vals when a new
    # journal of type bank/cash is created
    @api.model
    def _prepare_liquidity_account(self, name, company, currency_id, type):
        res = super(AccountJournal, self)._prepare_liquidity_account(
            name, company, currency_id, type
        )
        if type == "bank":
            parent_code = company.bank_account_code_prefix or ""
        else:
            parent_code = (
                company.cash_account_code_prefix
                or company.bank_account_code_prefix
                or ""
            )
        parent_id = self.env["account.account"].search(
            [("code", "=", str(parent_code.ljust(6, "0")))], limit=1
        )
        res["parent_id"] = parent_id and parent_id.id
        return res
