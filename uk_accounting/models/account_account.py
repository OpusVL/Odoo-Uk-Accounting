# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountAccountType(models.Model):
    _inherit = "account.account.type"

    type = fields.Selection(selection_add=[('view', 'View')])
    internal_group = fields.Selection(selection_add=[('view', 'View')])


class AccountAccount(models.Model):
    _inherit = "account.account"

    account_parent_id = fields.Many2one('account.account', 'Parent Account', ondelete="set null")


class AccountAccountTemplate(models.Model):
    _inherit = "account.account.template"

    account_parent_id = fields.Many2one('account.account.template', 'Parent Account', ondelete="set null")


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    # Inheriting base function to add the account_parent_id in vals
    def _get_account_vals(self, company, account_template, code_acc, tax_template_ref):
        res = super(AccountChartTemplate, self)._get_account_vals(company, account_template, code_acc, tax_template_ref)
        account_parent_id = account_template.account_parent_id and account_template.account_parent_id.id or False
        res['account_parent_id'] = account_parent_id
        return res


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # Inheriting base function to add the account_parent_id in vals when a new journal of type bank/cash is created
    @api.model
    def _prepare_liquidity_account(self, name, company, currency_id, type):
        res = super(AccountJournal, self)._prepare_liquidity_account(name, company, currency_id, type)
        if type == 'bank':
            parent_code = company.bank_account_code_prefix or ''
        else:
            parent_code = company.cash_account_code_prefix or company.bank_account_code_prefix or ''
        account_parent_id = self.env['account.account'].search([('code', '=', str(parent_code.ljust(6, '0')))], limit=1)
        res['account_parent_id'] = account_parent_id and account_parent_id.id
        return res



