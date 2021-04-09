from odoo import models


class ResGroups(models.Model):
    _inherit = "res.groups"

    def add_full_accounting_features(self):
        internal_user_grup = self.env.ref("base.group_user")
        internal_user_grup.write(
            {"implied_ids": [(4, self.env.ref("account.group_account_user").id)]}
        )
        return True
