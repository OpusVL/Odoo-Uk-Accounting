# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


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
                total_asset_months = diff_month(end_date, asset.date)
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
        # Fixed Asset revaluation entries
        move_lines = self.get_revaluation_move_lines()
        move_vals = self.get_move_vals(move_lines)
        move = self.env['account.move'].create(move_vals)
        move.post()
        asset_revaluation_data = {
            'asset_id': asset.id,
            'note': self.note,
            'name': self.name,
            'net_value': self.net_value,
            'revaluation_value': self.revaluation_value,
            'difference_value': self.difference_value,
            'revaluation_date': self.revaluation_date,
        }
        self.env['asset.revaluation.log'].create(asset_revaluation_data)
        asset.with_context(revaluation=True).write({
            'revaluation_occurred': True,
            'cumulative_revaluation_value':
                asset.cumulative_revaluation_value + self.difference_value,
            'revaluation_method_progress_factor': self.revaluation_method_progress_factor,
            'method_progress_factor': self.method_progress_factor,
        })
        asset.with_context(
            asset_value=self.revaluation_value,
        ).compute_depreciation_board(
            self.revaluation_date)
        return {'type': 'ir.actions.act_window_close'}

    def get_revaluation_move_lines(self):
        asset = self.get_asset()
        revaluation_move_lines = []
        prec = self.env['decimal.precision'].precision_get('Account')
        company_currency = asset.company_id.currency_id
        current_currency = asset.currency_id

        if asset.revaluation_line_ids:
            last_revaluated_date = asset.revaluation_line_ids.sorted(
                    key=lambda r: r.revaluation_date, reverse=True)[0].revaluation_date
            deprecated_amount_currency = sum(
                line.period_amount + line.revaluation_period_amount for line in
                asset.depreciation_line_ids.filtered(
                    lambda
                        x: x.depreciation_date < self.revaluation_date and
                           x.depreciation_date >= last_revaluated_date)) + \
                                         asset.value_alr_accumulated
        else:
            deprecated_amount_currency = sum(
                line.period_amount + line.revaluation_period_amount for line in
                asset.depreciation_line_ids.filtered(
                    lambda x: x.depreciation_date < self.revaluation_date)) + asset.value_alr_accumulated
        deprecated_amount = current_currency.with_context(
            date=self.revaluation_date).compute(
            deprecated_amount_currency,
            company_currency)
        reserve_loss_amount_currency = self.difference_value
        reserve_loss_amount = current_currency.with_context(
            date=self.revaluation_date).compute(
            reserve_loss_amount_currency,
            company_currency)
        if reserve_loss_amount:
            reserve_loss_line_item = {
                'name': '{}: Asset Equity Reserve'.format(
                    asset.name
                ) if reserve_loss_amount > 0 else '{}: Asset Loss'.format(
                    asset.name
                ),
                'account_id':
                    asset.category_id.account_revaluation_equity_id.id if
                    reserve_loss_amount > 0 else
                    asset.category_id.account_revaluation_loss_id.id,
                'credit': reserve_loss_amount if float_compare(
                    reserve_loss_amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'debit': -reserve_loss_amount if float_compare(
                    reserve_loss_amount, 0.0, precision_digits=prec) < 0 else 0.0,
                'journal_id': asset.category_id.journal_id.id,
                'partner_id': asset.partner_id.id,
                'currency_id': company_currency != current_currency and
                               current_currency.id or False,
                'amount_currency': company_currency != current_currency
                                   and reserve_loss_amount_currency or 0.0,
            }
            revaluation_move_lines.append(reserve_loss_line_item)
        if deprecated_amount:
            asset_deprecated_line_item = {
                'name': '{}: Asset Depreciation'.format(
                    asset.name
                ),
                'account_id': asset.category_id.account_depreciation_id.id,
                'credit': -deprecated_amount if float_compare(
                    deprecated_amount, 0.0, precision_digits=prec) < 0 else 0.0,
                'debit': deprecated_amount if float_compare(
                    deprecated_amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'journal_id': asset.category_id.journal_id.id,
                'partner_id': asset.partner_id.id,
                'currency_id': company_currency != current_currency and
                               current_currency.id or False,
                'amount_currency': company_currency != current_currency
                                   and deprecated_amount_currency or 0.0,
            }
            revaluation_move_lines.append(asset_deprecated_line_item)
        asset_value_currency = reserve_loss_amount_currency - deprecated_amount_currency
        asset_value = current_currency.with_context(
            date=self.revaluation_date).compute(
            asset_value_currency,
            company_currency)
        if asset_value:
            asset_value_line_item = {
                'name': '{}: Asset Value'.format(
                    asset.name
                ),
                'account_id': asset.category_id.account_asset_id.id,
                'credit': -asset_value if float_compare(
                    asset_value, 0.0, precision_digits=prec) < 0 else 0.0,
                'debit': asset_value if float_compare(
                    asset_value, 0.0, precision_digits=prec) > 0 else 0.0,
                'journal_id': asset.category_id.journal_id.id,
                'partner_id': asset.partner_id.id,
                'analytic_account_id':
                    asset.category_id.account_analytic_id.id if
                    asset.category_id.type == 'purchase' else False,
                'currency_id': company_currency != current_currency and
                               current_currency.id or False,
                'amount_currency': company_currency != current_currency
                                   and asset_value_currency or 0.0,
            }
            revaluation_move_lines.append(asset_value_line_item)
        return revaluation_move_lines

    def get_move_vals(self, move_lines):
        asset = self.get_asset()
        return {
            'ref': asset.code,
            'date': self.revaluation_date,
            'journal_id': asset.category_id.journal_id.id,
            'line_ids': [(0, 0, move_line) for move_line in move_lines],
            'asset_id': asset.id
        }

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
                lambda line: line.depreciation_date < self.revaluation_date and not line.move_id)
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
