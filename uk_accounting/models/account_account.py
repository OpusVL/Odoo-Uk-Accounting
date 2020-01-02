# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountAccountType(models.Model):
    _inherit = "account.account.type"

    type = fields.Selection(selection_add=[('view', 'View')])
    internal_group = fields.Selection(selection_add=[('view', 'View')])


class AccountAccount(models.Model):
    _inherit = "account.account"

    parent_id = fields.Many2one('account.account', 'Parent Account', ondelete="set null")



