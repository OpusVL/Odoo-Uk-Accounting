# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AssetRevaluation(models.TransientModel):
    _name = 'asset.revaluation'
    _description = 'Asset Revaluation'

    name = fields.Text(string='Reason', required=True)
    note = fields.Text(string='Notes')

    def confirm_asset_revaluation(self):
        self.ensure_one()
        asset_id = self.env.context.get('active_id', False)
        asset = self.env['account.asset.asset'].browse(asset_id)
        net_value = revaluation_value = difference_value = 0
        asset_revaluation_data = {
            'asset_id': asset_id,
            'note': self.note,
            'name': self.name,
            'net_value': net_value,
            'revaluation_value': revaluation_value,
            'difference_value': difference_value,
        }
        self.env['asset.revaluation.log'].create(asset_revaluation_data)
        asset.write({
            'revaluation_occurred': True,
        })
        return {'type': 'ir.actions.act_window_close'}
