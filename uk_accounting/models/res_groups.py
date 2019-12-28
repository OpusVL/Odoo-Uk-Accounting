# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class ResGroups(models.Model):
    _inherit = "res.groups"

    def add_full_accounting_features(self):
        internal_user_grup = self.env.ref('base.group_user')
        internal_user_grup.write({
            'implied_ids': [(4, self.env.ref('account.group_account_user').id)]
        })
        return True

