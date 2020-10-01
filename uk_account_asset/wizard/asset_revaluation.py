# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


def diff_month(d1, d2):
    return (d1.year - d2.year) * 12 + d1.month - d2.month


class AssetRevaluation(models.TransientModel):
    _name = 'asset.revaluation'
    _description = 'Asset Revaluation'

    name = fields.Text(string='Reason', required=True)
    note = fields.Text(string='Notes')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency')
    net_value = fields.Monetary(
        string='Net Asset Value',
    )
    gross_value = fields.Monetary(
        string='Gross Value',
    )
    revaluation_value = fields.Monetary(
        string='Asset Revaluation Value',
    )
    difference_value = fields.Monetary(
        string='Difference Value',
        compute='_compute_difference_value'
    )
    revaluation_date = fields.Date(
        string='Revaluation Date',
        required=True,
    )
    method_period = fields.Integer(
        string='Period Length',
    )
    revaluation_months = fields.Integer(
        string='Revaluation Months',
    )
    calc_revaluation_months = fields.Integer(
        string='Calculated Revaluation Months',
    )
    method_progress_factor = fields.Float(
        'Degressive Factor',
    )
    revaluation_method_progress_factor = fields.Float(
        'Revaluation Degressive Factor',
    )
    total_asset_months = fields.Integer(
        string='Total Asset Months',
    )
    asset_already_passed_months = fields.Integer(
        string='Already passed months',
    )

    @api.model
    def default_get(self, fields):
        res = super(AssetRevaluation, self).default_get(fields)
        asset = self.get_asset()
        if 'currency_id' in fields:
            res.update({'currency_id': asset.currency_id.id})
        if 'net_value' in fields:
            res.update({'net_value': asset.value_residual})
        if 'gross_value' in fields:
            res.update({'gross_value': asset.value})
        if 'method_progress_factor' in fields:
            res.update({'method_progress_factor': asset.method_progress_factor})
        if 'revaluation_date' in fields:
            unposted_lines = asset.depreciation_line_ids.filtered(
                    lambda line: not line.move_id)
            if unposted_lines:
                first_unposted_line = unposted_lines.sorted(
                    key=lambda r: r.depreciation_date)[0]
                end_date = unposted_lines.sorted(
                    key=lambda r: r.depreciation_date, reverse=True)[0].depreciation_date
                total_asset_months = diff_month(end_date, asset.date) + 1
                res.update({
                    'revaluation_date': first_unposted_line.depreciation_date,
                    'revaluation_months': len(unposted_lines) * asset.method_period,
                    'calc_revaluation_months': len(
                        unposted_lines) * asset.method_period,
                    'revaluation_method_progress_factor': asset.method_progress_factor * (total_asset_months/len(unposted_lines)),
                    'total_asset_months': total_asset_months,
                    'asset_already_passed_months': total_asset_months - len(
                        unposted_lines) * asset.method_period
                })
        if 'method_period' in fields:
            res.update({'method_period': asset.method_period})
        return res

    @api.depends("revaluation_value", "net_value")
    def _compute_difference_value(self):
        self.difference_value = self.revaluation_value - self.net_value

    def confirm_asset_revaluation(self):
        self.ensure_one()
        asset = self.get_asset()
        asset_revaluation_data = {
            'asset_id': asset.id,
            'note': self.note,
            'name': self.name,
            'net_value': self.net_value,
            'revaluation_value': self.revaluation_value,
            'difference_value': self.difference_value,
        }
        self.env['asset.revaluation.log'].create(asset_revaluation_data)
        asset.with_context(revaluation=True).write({
            'revaluation_occurred': True,
            'cumulative_revaluation_value':
                asset.cumulative_revaluation_value + self.difference_value,
            'revaluation_method_progress_factor': self.revaluation_method_progress_factor,
            'method_progress_factor': self.method_progress_factor,
        })
        asset.compute_depreciation_board(self.revaluation_date)
        return {'type': 'ir.actions.act_window_close'}

    @api.onchange("revaluation_date")
    def onchange_revaluation_date(self):
        asset = self.get_asset()
        if self.revaluation_date:
            unposted_lines = asset.depreciation_line_ids.filtered(
                lambda line: not line.move_id and
                             line.depreciation_date == self.revaluation_date)
            if not unposted_lines:
                raise UserError(
                    _(
                        "Revaluation date should be an unposted entry from "
                        "the existing board computation")
                )
            unposted_lines = asset.depreciation_line_ids.filtered(
                lambda line: line.depreciation_date >= self.revaluation_date)
            unposted_line_values = asset.depreciation_line_ids.filtered(
                lambda line: line.depreciation_date < self.revaluation_date)
            unposted_deprecated_sum = sum(
                line.period_amount + line.revaluation_period_amount for line in unposted_line_values)
            self.net_value = asset.value_residual - unposted_deprecated_sum
            self.with_context(revaluation_date=True).revaluation_months = self.calc_revaluation_months = len(
                unposted_lines
            )
            self.revaluation_method_progress_factor = self.method_progress_factor * (
                    self.total_asset_months/self.revaluation_months)
            self.asset_already_passed_months = self.total_asset_months - self.calc_revaluation_months

    def get_asset(self):
        asset_id = self.env.context.get('active_id', False)
        return self.env['account.asset.asset'].browse(asset_id)

    @api.onchange("revaluation_months")
    def onchange_revaluation_months(self):
        if not self._context.get('revaluation_date'):
            diff_months = self.revaluation_months - self.calc_revaluation_months
            self.total_asset_months += diff_months
            self.method_progress_factor = round(self.method_progress_factor * (
                self.calc_revaluation_months/self.revaluation_months
            ), 2)
            self.revaluation_method_progress_factor = self.method_progress_factor * (
                    self.total_asset_months / self.revaluation_months)
            self.calc_revaluation_months = self.revaluation_months
