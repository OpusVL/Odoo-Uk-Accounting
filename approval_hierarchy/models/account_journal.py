# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import AccessError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def import_statement(self):
        if not self.env.su and not self.env.user.has_group(
                "approval_hierarchy.import_bank_statement_role"):
            raise AccessError(
                _("You don't have access rights to perform a "
                  "Bank statement import."))
        return super(AccountJournal, self).import_statement()
