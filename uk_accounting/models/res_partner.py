# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    sort_code = fields.Char(tracking=True,)
    short_name = fields.Char(tracking=True,)
