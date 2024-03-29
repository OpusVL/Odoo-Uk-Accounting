from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    combined_payment = fields.Boolean(
        string="Combined Payment", related="company_id.combined_payment", readonly=False
    )


class ResCompany(models.Model):
    _inherit = "res.company"

    combined_payment = fields.Boolean(string="Use Combined Payment")
