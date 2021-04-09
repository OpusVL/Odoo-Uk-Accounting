from odoo import fields, models


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    sort_code = fields.Char()
    short_name = fields.Char()
