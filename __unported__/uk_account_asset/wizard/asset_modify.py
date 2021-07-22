# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AssetModify(models.TransientModel):
    _name = 'asset.modify'
    _description = 'Modify Asset'

    name = fields.Text(string='Reason', required=True)
    method_number = fields.Integer(string='Number of Depreciations',
                                   required=True)
    method_period = fields.Integer(string='Period Length')
    method_end = fields.Date(string='Ending date')
    asset_method_time = fields.Char(compute='_get_asset_method_time',
                                    string='Asset Method Time', readonly=True)
    value_accumulated = fields.Float('Value accumulated')
    date_value_acc = fields.Date('Depreciation Date')
    stock_account_input = fields.Many2one('account.account',
                                          'Intermediate account', required=True)
    stock_account_output = fields.Many2one('account.account',
                                           'Depreciation Account', required=True)
    stock_journal = fields.Many2one('account.journal',
                                    'Stock journal', required=True)

    def _get_asset_method_time(self):
        if self.env.context.get('active_id'):
            asset = self.env['account.asset.asset'].browse(self.env.context.get('active_id'))
            self.asset_method_time = asset.method_time

    @api.model
    def default_get(self, fields):
        res = super(AssetModify, self).default_get(fields)
        asset_id = self.env.context.get('active_id')
        asset = self.env['account.asset.asset'].browse(asset_id)
        if 'name' in fields:
            res.update({'name': asset.name})
        if 'method_number' in fields and asset.method_time == 'number':
            res.update({'method_number': asset.method_number})
        if 'method_period' in fields:
            res.update({'method_period': asset.method_period})
        if 'method_end' in fields and asset.method_time == 'end':
            res.update({'method_end': asset.method_end})
        if 'value_accumulated' in fields:
            res.update({'value_accumulated': asset.product_id.standard_price})
        if 'stock_account_output' in fields:
            res.update({'stock_account_output': asset.category_id.account_depreciation_id.id})
        if 'stock_journal' in fields:
            res.update({'stock_journal':asset.category_id.journal_id.id})
        if self.env.context.get('active_id'):
            active_asset = self.env['account.asset.asset'].browse(self.env.context.get('active_id'))
            res['asset_method_time'] = active_asset.method_time
        return res

    def modify(self):
        """ Modifies the duration of asset for calculating depreciation
        and maintains the history of old values, in the chatter.
        """
        asset_id = self.env.context.get('active_id', False)
        asset = self.env['account.asset.asset'].browse(asset_id)
        old_values = {
            'method_number': asset.method_number,
            'method_period': asset.method_period,
            'method_end': asset.method_end,
            'value_accumulated': asset.value_alr_accumulated,
            'date_value_alr_acc': asset.date_value_alr_acc,
        }
        asset_vals = {
            'method_number': self.method_number,
            'method_period': self.method_period,
            'method_end': self.method_end,
            'value_accumulated': self.value_accumulated,
            'date_value_alr_acc': self.date_value_acc,
        }
        asset.write(asset_vals)
        asset.compute_depreciation_board()
        datas = {
            'value_accumulated': self.value_accumulated,
            'stock_output_account': self.stock_account_output.id,
            'stock_input_account': self.stock_account_input.id,
            'stock_journal': self.stock_journal.id,
            'date_value_acc': self.date_value_acc,
        }
        asset.do_change_accumulated_account(datas)
        tracked_fields = self.env['account.asset.asset'].fields_get(
            ['method_number', 'method_period', 'method_end'])
        changes, tracking_value_ids = asset._message_track(
            tracked_fields, old_values)
        if changes:
            asset.message_post(subject=_('Depreciation board modified'),
                               body=self.name,
                               tracking_value_ids=tracking_value_ids)
        return {'type': 'ir.actions.act_window_close'}
