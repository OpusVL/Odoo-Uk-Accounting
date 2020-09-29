# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AssetRevaluation(models.TransientModel):
    _name = 'asset.revaluation'
    _description = 'Asset Revaluation'

    name = fields.Text(string='Reason', required=True)

    def confirm_asset_revaluation(self):

        return {'type': 'ir.actions.act_window_close'}
