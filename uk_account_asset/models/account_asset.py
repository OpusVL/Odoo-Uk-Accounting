# -*- coding: utf-8 -*-

from datetime import date, datetime
import time
from odoo import api, fields, models, _
import calendar
from calendar import monthrange
from datetime import timedelta
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from dateutil.relativedelta import relativedelta
from odoo.tools import float_is_zero, float_compare


def month_difference(d1, d2):
    difference = 0
    while True:
        mdays = monthrange(d1.year, d1.month)[1]
        d1 += timedelta(days=mdays)
        if d1 <= d2:
            difference += 1
        else:
            break
    return difference


class AccountAssetGroup(models.Model):
    _name = 'account.asset.group'

    name = fields.Char(required=True, index=True, string="Asset Group")


class AccountAssetCategory(models.Model):
    _name = 'account.asset.category'
    _description = 'Asset category'

    active = fields.Boolean(default=True)
    name = fields.Char(
        required=True,
        index=True,
        string="Asset Type")
    code = fields.Char(
        required=True,
        index=True,
        string="Category Code")
    account_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account')
    account_asset_id = fields.Many2one(
        'account.account',
        string='Asset Account',
        required=True,
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
        help="Account used to record the purchase of the asset "
             "at its original price.")
    account_depreciation_id = fields.Many2one(
        'account.account',
        string='Depreciation Entries: Asset Account',
        required=True,
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
        help="Account used in the depreciation entries, to decrease "
             "the asset value.")
    account_depreciation_expense_id = fields.Many2one(
        'account.account',
        string='Depreciation Entries: Expense Account',
        required=True,
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
        help="Account used in the periodical entries, to record a part of "
             "the asset as expense.")
    account_net_value_id = fields.Many2one(
        'account.account',
        string='Net Value Account',)
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company)
    method = fields.Selection(
        [('linear', 'Linear'), ('degressive', 'Degressive')],
        string='Computation Method',
        required=True,
        default='linear',
        help="Choose the method to use to compute the amount of depreciation "
             "lines * Linear: Calculated on basis of: Gross Value / "
             "Number of Depreciations * Degressive: Calculated on basis of: "
             "Residual Value * Degressive Factor")
    method_number = fields.Integer(
        string='Number of Depreciations',
        default=5,
        help="The number of depreciations needed to depreciate your asset")
    method_period = fields.Integer(
        string='Period Length',
        default=1,
        required=True,
        help="State here the time between 2 depreciations, in months")
    method_progress_factor = fields.Float(
        'Degressive Factor',
        default=0.3)
    method_time = fields.Selection(
        [('number', 'Number of Entries'), ('end', 'Ending Date')],
        string='Time Method',
        required=True,
        default='number',
        help="Choose the method to use to compute the dates and number of "
             "entries. * Number of Entries: Fix the number of entries and "
             "the time between 2 depreciations. * Ending Date: Choose the time "
             "between 2 depreciations and the date the depreciations "
             "won't go beyond.")
    method_end = fields.Date('Ending date')
    prorata = fields.Boolean(
        string='Depreciate from Date of asset',
        help='Indicates that the first depreciation entry for this asset have '
             'to be done from the purchase date instead of the first of January'
    )
    open_asset = fields.Boolean(
        string='Auto-confirm Assets',
        help="Check this if you want to automatically confirm the assets of "
             "this category when created by invoices.")
    group_entries = fields.Boolean(
        string='Group Journal Entries',
        help="Check this if you want to group the generated entries "
             "by categories.")
    type = fields.Selection(
        [('sale', 'Sale: Revenue Recognition'), ('purchase', 'Purchase: Asset')],
        required=True,
        index=True,
        default='purchase')
    years = fields.Integer('# of Years')
    year_depreciation = fields.Boolean('Year Depreciation')
    border_amount = fields.Monetary('Border value')
    min_amount = fields.Monetary('Minimum Value')
    currency_id = fields.Many2one(
        'res.currency',
        'Currency',
        required=True,
        default=lambda self: self.env.company.currency_id)
    account_depreciation_accumulated_id = fields.Many2one(
        'account.account',
        string='Accumulated Intermediate Account',
        required=True,
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],)
    account_depreciation_disposal_id = fields.Many2one(
        'account.account',
        string='Asset Disposal Account',
        required=True,
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],)
    asset_revaluation = fields.Boolean(
        string='Asset Revaluation',
        help='If checked it will allow by default to apply asset revaluation'
    )
    account_revaluation_equity_id = fields.Many2one(
        'account.account',
        string='Revaluation Equity Reserve',
        required=True,
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],)
    account_revaluation_loss_id = fields.Many2one(
        'account.account',
        string='Revaluation Loss',
        required=True,
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)], )

    def name_get(self):
        res = []
        for category in self:
            name = "[{}] {}".format(category.code, category.name)
            res.append((category.id, name))
        return res

    @api.onchange('account_asset_id')
    def onchange_account_asset(self):
        if self.type == "purchase":
            self.account_depreciation_id = self.account_asset_id
        else:
            self.account_depreciation_expense_id = self.account_asset_id

    @api.onchange('type')
    def onchange_type(self):
        if self.type == 'sale':
            self.prorata = True
            self.method_period = 1
        else:
            self.method_period = 12

    @api.onchange('method_time')
    def _onchange_method_time(self):
        if self.method_time != 'number':
            self.prorata = False

    @api.onchange('method')
    def onchange_method(self):
        self.year_depreciation = False
        self.years = 1
        if self.method == 'linear':
            self.border_amount = 0.0
            self.min_amount = 0.0

    @api.onchange('year_depreciation', 'years', 'method_period')
    def onchange_year_depreciation(self):
        if self.year_depreciation and self.years:
            self.method_progress_factor = 1 / self.years
            if self.method_period:
                self.method_number = self.years * 12 / self.method_period


class AccountAssetAsset(models.Model):
    _name = 'account.asset.asset'
    _description = 'Asset/Revenue Recognition'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('move_ids')
    def _compute_move_ids(self):
        for asset in self:
            asset.move_count = len(asset.move_ids)

    name = fields.Char(
        string='Asset Name',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]})
    code = fields.Char(
        string='Asset ID',
        size=32,
        readonly=True,
        copy=False,
        states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one(
        'res.currency',
        'Currency',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.company.currency_id)
    value = fields.Monetary(
        string='Gross Value',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        states={'draft': [('readonly', False)]},
        readonly=True,
        default=lambda self: self.env.company)
    category_id = fields.Many2one(
        'account.asset.category',
        string='Category',
        required=True,
        change_default=True,
        readonly=True,
        states={'draft': [('readonly', False)]})
    group_id = fields.Many2one(
        'account.asset.group',
        string='Asset Group',
        required=True,
        change_default=True,
        readonly=True,
        states={'draft': [('readonly', False)]})
    date = fields.Date(
        string='Date of asset',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=fields.Date.context_today, )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('open', 'Running'),
            ('close', 'Close'),
            ('outservice', 'Out of service')
        ],
        'Status',
        required=True,
        copy=False,
        default='draft',
        help="When an asset is created, the status is 'Draft'. If the asset "
             "is confirmed, the status goes in 'Running' and the depreciation "
             "lines can be posted in the accounting.You can manually close an "
             "asset when the depreciation is over. If the last line of "
             "depreciation is posted, the asset automatically "
             "goes in that status.")
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        readonly=True,
        states={'draft': [('readonly', False)]})
    method = fields.Selection(
        [('linear', 'Linear'), ('degressive', 'Degressive')],
        string='Computation Method',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default='linear',
        help="Choose the method to use to compute the amount of depreciation "
             "lines. * Linear: Calculated on basis of: Gross Value / Number of "
             "Depreciations * Degressive: Calculated on basis of: "
             "Residual Value * Degressive Factor")
    method_number = fields.Integer(
        string='Number of Depreciations',
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=5,
        help="The number of depreciations needed to depreciate your asset")
    method_period = fields.Integer(
        string='Number of Months in a Period',
        required=True,
        readonly=True,
        default=1,
        states={'draft': [('readonly', False)]},
        help="The amount of time between two depreciations, in months")
    method_end = fields.Date(
        string='Ending Date',
        readonly=True,
        states={'draft': [('readonly', False)]})
    method_progress_factor = fields.Float(
        string='Degressive Factor',
        readonly=True,
        states={'draft': [('readonly', False)]})
    method_time = fields.Selection(
        [('number', 'Number of Entries'), ('end', 'Ending Date')],
        string='Time Method',
        required=True,
        readonly=True,
        default='number',
        states={'draft': [('readonly', False)]},
        help="Choose the method to use to compute the dates and number of "
             "entries. * Number of Entries: Fix the number of entries and the "
             "time between 2 depreciations. * Ending Date: Choose the time "
             "between 2 depreciations and the date the depreciations "
             "won't go beyond.")
    value_residual = fields.Monetary(
        compute='_compute_amount',
        method=True,
        store=True,
        string='Residual Value')
    prorata = fields.Boolean(
        string='Depreciate from Date of asset',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Indicates that the first depreciation entry for this asset have '
             'to be done from the purchase date instead of the first '
             'January / Start date of fiscal year')
    salvage_value = fields.Monetary(
        string='Salvage Value',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="It is the amount you plan to have that you cannot depreciate.")
    type = fields.Selection(
        related="category_id.type",
        string='Type',
        store=True)
    computation_type = fields.Selection(
        [('legal', 'Legal'), ('management', 'Management')],
        string='Computation Type',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default='legal')
    value_alr_accumulated = fields.Monetary(
        'Value Already Accumulated ',
        readonly=True,
        states={'draft': [('readonly', False)]})
    date_value_alr_acc = fields.Date(
        'Depreciation Date',
        readonly=True,
        states={'draft': [('readonly', False)]})
    border_amount = fields.Float(
        string='Border Amount',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="It is the amount you plan to have that you cannot depreciate.")
    years = fields.Integer(
        '# of Years',
        readonly=True,
        states={'draft': [('readonly', False)]})
    year_depreciation = fields.Boolean(
        'Year Depreciation',
        readonly=True,
        states={'draft': [('readonly', False)]})
    product_id = fields.Many2one(
        'product.product',
        string='Product')
    value_accumulated = fields.Float(
        compute='_compute_amount',
        store=True,
        method=True,
        digits=0,
        string='Accumulated Value')
    serial_nr = fields.Char('Serial no')
    move_count = fields.Integer(
        string='Journal entries',
        compute='_compute_move_ids')
    active = fields.Boolean(default=True)
    note = fields.Text()
    depreciation_line_ids = fields.One2many(
        'account.asset.depreciation.line',
        'asset_id',
        string='Depreciation Lines',
        readonly=True,
        states={'draft': [('readonly', False)], 'open': [('readonly', False)]})
    move_ids = fields.One2many(
        'account.move',
        'asset_id',
        string='Journal entries')
    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking',
        states={'draft': [('readonly', False)]},
        copy=False)
    asset_revaluation = fields.Boolean(
        string='Asset Revaluation',
        help='If checked it will allow by default to apply asset revaluation',
        readonly=True,
        states={'draft': [('readonly', False)], 'open': [('readonly', False)]},
    )
    revaluation_occurred = fields.Boolean(
        string='Asset Revaluation Occurred',
        copy=False,
    )
    cumulative_revaluation_value = fields.Monetary(
        'Cumulative Revaluation Value ',
        readonly=True,
        copy=False,
    )
    revaluation_line_ids = fields.One2many(
        'asset.revaluation.log',
        'asset_id',
        string='Asset Revaluation Logs',
        readonly=True,
        copy=False,
        states={'open': [('readonly', False)]})
    revaluation_method_progress_factor = fields.Float(
        string='Revaluation Factor', copy=False)

    def unlink(self):
        for asset in self:
            if asset.state in ['open', 'close']:
                raise UserError(_(
                    'You cannot delete a document which is in %s state.') % (
                    asset.state,))
            if asset.code:
                raise UserError(_(
                    'You cannot delete a fixed asset which is confirmed once, '
                    'We suggest to archive it instead'))
            for depreciation_line in asset.depreciation_line_ids:
                if depreciation_line.move_id:
                    raise UserError(_('You cannot delete a document that '
                                      'contains posted entries.'))
        return super(AccountAssetAsset, self).unlink()

    def _get_last_depreciation_date(self):
        """
        @param id: ids of a account.asset.asset objects
        @return: Returns a dictionary of the effective dates of the last
        depreciation entry made for given asset ids.
        If there isn't any, return the purchase date of this asset
        """
        if self.depreciation_line_ids:
            depreciation_date = self.depreciation_line_ids.sorted(
                    key=lambda r: r.depreciation_date, reverse=True)[0].depreciation_date
        else:
            depreciation_date = self.date_value_alr_acc or self.date
        return depreciation_date

    def _compute_board_undone_dotation_nb(self, depreciation_date):
        undone_dotation_number = self.method_number
        if self.method_time == 'end':
            end_date = self.method_end
            undone_dotation_number = 0
            while depreciation_date <= end_date:
                depreciation_date = date(
                    depreciation_date.year, depreciation_date.month,
                    depreciation_date.day) + relativedelta(
                    months=+self.method_period)
                undone_dotation_number += 1
        if self.prorata:
            undone_dotation_number += 1
        return undone_dotation_number

    def compute_depreciation_board(self, revaluation_date=False,):
        self.ensure_one()
        depreciation_line = self.env['account.asset.depreciation.line']
        if not revaluation_date:
            old_depreciation_lines = depreciation_line.search([
                ('asset_id', '=', self.id), ('move_id', '=', False)])
        else:
            old_depreciation_lines = depreciation_line.search([
                ('asset_id', '=', self.id),
                ('depreciation_date', '>=', revaluation_date)
            ])
        old_depreciation_lines.unlink()
        if not self.value_residual:
            return False
        if not self.method_progress_factor:
            return False
        amount_to_depr = remaining_value = self._context.get(
            'asset_value') if self._context.get(
            'asset_value') else self.value_residual
        depreciation_factor = self.value
        revaluation_factor = amount_to_depr if self._context.get(
            'asset_value') else self.value
        depreciation_date = self._get_last_depreciation_date()
        depreciation_date = (depreciation_date - relativedelta(
            days=depreciation_date.day - 1)) + relativedelta(months=1)
        depreciation_move_date = (depreciation_date + relativedelta(
            months=1) - relativedelta(days=1))
        i = 0
        sequence = 0
        depreciated_value = 0
        period_amount = 0
        period_revaluation_amount = 0
        total_deprecated_revaluation_amount = 0
        if self.method_period > 12 or self.method_period == 1 or 12 % self.method_period:
            period_months = [i for i in range(1, 13)]
        else:
            total_list = [i for i in range(1, 13)]
            period_months = [x for x in total_list if x % self.method_period == 0]
        while amount_to_depr > self.border_amount and \
                amount_to_depr > self.category_id.min_amount:
            i += 1
            sequence += 1
            depreciation_amount = depreciation_factor * self.method_progress_factor
            revaluation_amount = revaluation_factor * self.revaluation_method_progress_factor if \
                self._context.get('asset_value') else \
                revaluation_factor * self.method_progress_factor
            loop_number = 13 - depreciation_date.month
            amount_per_month = depreciation_amount / 12
            revaluation_amount_per_month = revaluation_amount/12 - amount_per_month
            if self.method == 'degressive':
                depreciation_factor = depreciation_factor - loop_number * amount_per_month
                revaluation_factor = revaluation_factor - loop_number * revaluation_amount_per_month
            for j in range(0, loop_number):
                amount_to_depr = amount_to_depr - amount_per_month - revaluation_amount_per_month
                period_amount += amount_per_month
                period_revaluation_amount += revaluation_amount_per_month
                if depreciation_move_date.month in period_months:
                    sequence += 1
                    if period_amount > remaining_value - period_revaluation_amount:
                        period_amount = remaining_value - period_revaluation_amount
                    vals = {
                        'amount': amount_per_month + revaluation_amount_per_month,
                        'asset_id': self.id,
                        'sequence': sequence,
                        'name': str(self.id) + '/' + str(i),
                        'depreciation_date':
                            depreciation_move_date.strftime('%Y-%m-%d'),
                        'period_amount': period_amount,
                        'revaluation_period_amount': period_revaluation_amount,
                        'remaining_value': remaining_value,
                        'depreciated_value':
                            self.value + self.cumulative_revaluation_value - remaining_value,
                    }
                    total_deprecated_revaluation_amount += period_revaluation_amount
                    remaining_value -= (
                            period_amount + period_revaluation_amount)
                    depreciated_value += period_amount + period_revaluation_amount
                    depreciation_line.create(vals)
                    period_amount = 0
                    period_revaluation_amount = 0
                depreciation_date = (depreciation_date + relativedelta(
                    months=1))
                depreciation_move_date = (depreciation_date + relativedelta(
                    months=1) - relativedelta(days=1))
                if remaining_value < 0.01:
                    return True
        depreciation_amount = amount_to_depr - self.cumulative_revaluation_value + total_deprecated_revaluation_amount
        revaluation_depreciation_amount = self.cumulative_revaluation_value - total_deprecated_revaluation_amount
        loop_number = 13 - depreciation_date.month
        amount_per_month = round(depreciation_amount / loop_number, 2)
        revaluation_amount_per_month = round(
            revaluation_depreciation_amount / loop_number, 2)
        period_amount = 0
        period_revaluation_amount = 0
        for j in range(0, loop_number):
            amount_to_depr = amount_to_depr - amount_per_month - revaluation_amount_per_month
            period_amount += amount_per_month
            period_revaluation_amount += revaluation_amount_per_month
            if depreciation_move_date.month in period_months:
                sequence += 1
                if period_amount > remaining_value - revaluation_amount_per_month:
                    period_amount = remaining_value - revaluation_amount_per_month
                elif j == loop_number - 1:
                    period_amount = remaining_value - revaluation_amount_per_month
                vals = {
                    'amount': amount_per_month + revaluation_amount_per_month,
                    'asset_id': self.id,
                    'sequence': sequence,
                    'name': str(self.id) + '/' + str(i),
                    'remaining_value': remaining_value,
                    'depreciated_value': self.value_residual - remaining_value,
                    'revaluation_period_amount': period_revaluation_amount,
                    'depreciation_date':
                        depreciation_move_date.strftime('%Y-%m-%d'),
                    'period_amount': period_amount,
                }
                remaining_value -= (period_amount + period_revaluation_amount)
                depreciated_value += period_amount + period_revaluation_amount
                period_amount = 0
                period_revaluation_amount = 0
                depreciation_line.create(vals)
            depreciation_date = (depreciation_date + relativedelta(
                months=1))
            depreciation_move_date = (depreciation_date + relativedelta(
                months=1) - relativedelta(days=1))
        return True

    def action_view_account_move(self):
        """
        :return: Form view of account move if there is only one account move
        created , and tree view if there are more than one account moves
        created. The function is triggered when clicking the button on account
        asset form view.
        """
        action = self.env.ref('account.action_move_line_form').read()[0]

        moves = self.mapped('move_ids')
        if len(moves) > 1:
            action['domain'] = [('id', 'in', moves.ids)]
        elif moves:
            action['views'] = [
                (self.env.ref('account.view_move_form').id, 'form')
            ]
            action['res_id'] = moves.id
        return action

    def do_change_accumulated_account(self, datas):
        """ Changes the Standard Price of Product and creates an account move
        accordingly.
        @param datas : dict. contain default datas like new_price,
        stock_output_account, stock_input_account, stock_journal
        @param context: A standard dictionary
        @return:

        """
        move_obj = self.env['account.move']

        new_price = datas.get('value_accumulated', 0.0)
        stock_output_acc = datas.get('stock_output_account', False)
        stock_input_acc = datas.get('stock_input_account', False)
        journal_id = datas.get('stock_journal', False)
        date = datas.get('date_value_acc', False)
        for rec_id in self:
            if new_price > 0.0:
                line_val1 = {'date':date,
                             'name': self.name,
                             'account_id': stock_input_acc,
                             'debit': new_price}
                line_val2 = {'date':date,
                             'name': self.name,
                             'account_id': stock_output_acc,
                             'credit': new_price}
                move_id = move_obj.create({'date':date,
                                           'journal_id': journal_id,
                                           'company_id': self.company_id.id,
                                           'line_ids': [
                                               (0, 0, line_val1),
                                               (0, 0, line_val2)
                                           ],
                                           'asset_id': self.id,
                                           })
                move_id.post()
            rec_id.write({'value_alr_accumulated': new_price,
                          'date_value_alr_acc': date})
        return True

    def validate(self):
        if not self.code:
            code = self.get_asset_code()
            self.write({'state': 'open', 'code': code})
        else:
            self.write({'state': 'open'})
        asset_fields = [
            'method',
            'method_number',
            'method_period',
            'method_end',
            'method_progress_factor',
            'method_time',
            'salvage_value',
        ]
        ref_tracked_fields = self.env['account.asset.asset'].fields_get(
            asset_fields)
        for asset in self:
            tracked_fields = ref_tracked_fields.copy()
            if asset.method == 'linear':
                del(tracked_fields['method_progress_factor'])
            if asset.method_time != 'end':
                del(tracked_fields['method_end'])
            else:
                del(tracked_fields['method_number'])
            dummy, tracking_value_ids = asset._message_track(
                tracked_fields, dict.fromkeys(asset_fields))
            asset.message_post(subject=_('Asset created'),
                               tracking_value_ids=tracking_value_ids)

    def set_to_close(self):
        for asset in self:
            unposted_depreciation_line_ids = asset.depreciation_line_ids.filtered(
                lambda x: not x.move_check).sorted(
                lambda line: line.depreciation_date)
            if unposted_depreciation_line_ids:
                old_values = {
                    'method_end': asset.method_end,
                    'method_number': asset.method_number,
                }

                total_period_amount = sum(
                    depreciation_line.period_amount for
                    depreciation_line in unposted_depreciation_line_ids)
                total_revaluation_period_amount = sum(
                    depreciation_line.revaluation_period_amount
                    for depreciation_line in unposted_depreciation_line_ids)
                depreciated_value = unposted_depreciation_line_ids[0].depreciated_value
                # Remove all unposted depr. lines
                commands = [
                    (2, line_id.id, False) for line_id in unposted_depreciation_line_ids]

                # Create a new depr. line with the residual amount and post it
                sequence = len(asset.depreciation_line_ids) - len(
                    unposted_depreciation_line_ids) + 1
                today = datetime.today().strftime(DF)
                vals = {
                    'amount': asset.value_residual,
                    'period_amount': total_period_amount,
                    'revaluation_period_amount': total_revaluation_period_amount,
                    'asset_id': asset.id,
                    'sequence': sequence,
                    'name': (asset.code or '') + '/' + str(sequence),
                    'remaining_value': 0,
                    'depreciated_value': depreciated_value,
                    'depreciation_date': today,
                }
                commands.append((0, False, vals))
                asset.write({'depreciation_line_ids': commands,
                             'method_end': today, 'method_number': sequence})
                tracked_fields = self.env['account.asset.asset'].fields_get(
                    ['method_number', 'method_end'])
                changes, tracking_value_ids = asset._message_track(
                    tracked_fields, old_values)
                if changes:
                    asset.message_post(subject=_('Asset sold or disposed. Accounting entry awaiting for validation.'), tracking_value_ids=tracking_value_ids)
                asset.depreciation_line_ids[-1].create_disposal_move(
                    post_move=True)
        return True

    def set_to_draft(self):
        if self.mapped('move_ids'):
            self.mapped('move_ids').button_cancel()
            self.mapped('move_ids').unlink()
        if self.mapped('depreciation_line_ids'):
            self.mapped('depreciation_line_ids').unlink()
        self.write({'state': 'draft', 'value_alr_accumulated': 0,
                    'date_value_alr_acc': False})

    def set_to_open(self):
        if self.depreciation_line_ids:
            for depreciation_line in self.depreciation_line_ids:
                depreciation_line.write({'state': 'confirm'})
        self.write({'state': 'open'})
        
    def get_asset_code(self):
        active_asset_ids = self.search([
            ('code', '!=', False),
            ('category_id', '=', self.category_id.id)
        ])
        archive_asset_ids = self.search([
            ('code', '!=', False),
            ('category_id', '=', self.category_id.id),
            ('active', '=', False)
        ])
        sequence = len(active_asset_ids) + len(archive_asset_ids) + 1
        no_digits = len(str(sequence)) if sequence >= 10000 else 4
        code = '{}{}'.format(self.category_id.code, str(sequence).zfill(
            no_digits))
        return code

    @api.depends('value', 'salvage_value', 'depreciation_line_ids.move_check',
                 'depreciation_line_ids.amount', 'value_alr_accumulated')
    def _compute_amount(self):
        for asset in self:
            total_amount = 0.0
            for line in asset.depreciation_line_ids:
                if line.move_check:
                    total_amount += line.amount
            asset.value_accumulated = total_amount
            asset.value_residual = asset.cumulative_revaluation_value + asset.value - total_amount - \
                              asset.salvage_value - asset.value_alr_accumulated

    @api.onchange('company_id')
    def onchange_company_id(self):
        self.currency_id = self.company_id.currency_id.id

    @api.constrains('prorata', 'method_time')
    def _check_prorata(self):
        if self.prorata and self.method_time != 'number':
            raise ValidationError(_('Prorata temporis can be applied only for '
                                    'time method "number of depreciations".'))

    @api.onchange('category_id')
    def onchange_category_id(self):
        if self.category_id:
            self.method = self.category_id.method
            self.method_number = self.category_id.method_number
            self.method_time = self.category_id.method_time
            self.method_progress_factor = self.category_id.method_progress_factor
            self.method_end = self.category_id.method_end
            self.year_depreciation = self.category_id.year_depreciation
            self.years = self.category_id.years
            self.asset_revaluation = self.category_id.asset_revaluation

    @api.onchange('method_time')
    def onchange_method_time(self):
        if self.method_time != 'number':
            self.prorata = False

    @api.onchange('method')
    def onchange_method(self):
        self.year_depreciation = False
        self.years = 1
        if self.method == 'linear':
            self.border_amount = 0.0

    @api.onchange('year_depreciation', 'years', 'method_period')
    def onchange_year_depreciation(self):
        if self.year_depreciation and self.years:
            self.method_progress_factor = 1 / self.years
            if self.method_period:
                self.method_number = self.years * 12 / self.method_period

    @api.onchange('value', 'category_id')
    def onchange_value(self):
        if self.category_id:
            self.border_amount = self.value * self.category_id.border_amount/100

    def copy_data(self, default=None):
        if default is None:
            default = {}
        default['name'] = self.name + _(' (copy)')
        return super(AccountAssetAsset, self).copy_data(default)

    def _compute_entries(self, date_end, date_start,
                         log_id, accounting_date, group_entries=False):
        if date_start:
            depreciation_ids = self.env['account.asset.depreciation.line'].search([
                ('asset_id', 'in', self.ids),
                ('depreciation_date', '>=', date_start),
                ('depreciation_date', '<=', date_end),
                ('move_check', '=', False)])
        else:
            depreciation_ids = self.env['account.asset.depreciation.line'].search([
                ('asset_id', 'in', self.ids),
                ('depreciation_date', '<=', date_end),
                ('move_check', '=', False)])
        if group_entries:
            return depreciation_ids.create_grouped_move()
        return depreciation_ids.create_move(
            post_move=True,
            log_id=log_id,
            accounting_date=accounting_date,
        )

    @api.model
    def create(self, vals):
        if 'product_id' in vals and vals['product_id']:
            product=self.env['product.product'].search([
                ('id', '=', vals['product_id'])]
            )
            sasia=product.qty_available
            aset_ids=self.search([
                ('product_id', '=', vals['product_id']),
                ('state', '!=', 'outservice')])
            if len(aset_ids) >= sasia:
                raise UserError(_('Cannot create more assets '
                                  'than the available quantity!') )
        if vals.get('value_alr_accumulated', 0.0) and vals.get(
                'date_value_alr_acc', False):
            # remove this fields from vals and modify asset with these values after created
            value_alr_accumulated = vals.get('value_alr_accumulated', 0.0)
            date_value_alr_acc = vals.get('date_value_alr_acc', 0.0)
            vals.pop('date_value_alr_acc')
            vals.pop('value_alr_accumulated')
            asset = super(AccountAssetAsset, self.with_context(
                mail_create_nolog=True)).create(vals)
            datas = {
                'value_accumulated': value_alr_accumulated,
                'stock_output_account': asset.category_id.account_depreciation_id.id,
                'stock_input_account': asset.category_id.account_depreciation_accumulated_id.id,
                'stock_journal': asset.category_id.journal_id.id,
                'date_value_acc': date_value_alr_acc,
            }
            asset.onchange_category_id()
            asset.do_change_accumulated_account(
                datas
            )
            asset.compute_depreciation_board()
        else:
            asset = super(AccountAssetAsset, self.with_context(
                mail_create_nolog=True)).create(vals)
            asset.onchange_category_id()
            asset.compute_depreciation_board()
        return asset

    def write(self, vals):
        if 'active' in vals:
            if self.state != 'draft':
                raise UserError(
                    _('Cannot Activate/Archive the asset, expect draft state!'))
        res = super(AccountAssetAsset, self).write(vals)
        if not self._context.get('revaluation') and 'depreciation_line_ids' not in vals and 'state' not in vals:
            for rec in self:
                rec.compute_depreciation_board()
        return res

    def open_entries(self):
        move_ids = []
        for asset in self:
            for depreciation_line in asset.depreciation_line_ids:
                if depreciation_line.move_id:
                    move_ids.append(depreciation_line.move_id.id)
        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_ids)],
        }


class AccountAssetDepreciationLine(models.Model):
    _name = 'account.asset.depreciation.line'
    _description = 'Asset depreciation line'

    name = fields.Char(
        string='Depreciation Name',
        required=True,
        index=True)
    sequence = fields.Integer(required=True)
    asset_id = fields.Many2one(
        'account.asset.asset',
        string='Asset',
        required=True,
        ondelete='cascade')
    currency_id = fields.Many2one(
        'res.currency',
        related='asset_id.currency_id',
        string='Currency')
    parent_state = fields.Selection(
        related='asset_id.state',
        string='State of Asset')
    amount = fields.Monetary(
        string='Current Depreciation',
        required=True)
    remaining_value = fields.Monetary(
        string='Next Period Depreciation',
        required=True)
    depreciated_value = fields.Monetary(
        string='Cumulative Depreciation',
        required=True)
    depreciation_date = fields.Date(
        'Depreciation Date',
        index=True)
    move_id = fields.Many2one(
        'account.move',
        string='Depreciation Entry')
    move_check = fields.Boolean(
        compute='_get_move_check',
        string='Linked',
        track_visibility='always',
        store=True)
    move_posted_check = fields.Boolean(
        compute='_get_move_posted_check',
        string='Posted',
        store=True,
        track_visibility='always',)
    period_amount = fields.Monetary(
        string='Current Depreciation Amount',
        required=True)
    revaluation_period_amount = fields.Monetary(
        string='Revaluation Amount',
        required=True)

    @api.depends('move_id')
    def _get_move_check(self):
        for line in self:
            line.move_check = bool(line.move_id)

    @api.depends('move_id.state')
    def _get_move_posted_check(self):
        for line in self:
            line.move_posted_check = True if line.move_id and line.move_id.state == 'posted' else False

    def create_move(self, post_move=True, log_id=False, accounting_date=False):
        created_moves = self.env['account.move']
        for line in self:
            move_lines = line.get_move_lines(accounting_date)
            move_vals = line.get_move_vals(move_lines, log_id)
            move = self.env['account.move'].create(move_vals)
            line.write({'move_id': move.id, 'move_check': True})
            created_moves |= move
        if post_move and created_moves:
            for created_move in created_moves:
                created_move.post()
        return [x.id for x in created_moves]

    def create_disposal_move(self, post_move=True):
        created_moves = self.env['account.move']
        for line in self:
            move_lines = line.get_disposal_move_lines()
            move_vals = line.get_move_vals(move_lines)
            move = self.env['account.move'].create(move_vals)
            line.write({'move_id': move.id, 'move_check': True})
            created_moves |= move
        if post_move and created_moves:
            for created_move in created_moves:
                created_move.post()
        return True

    def get_move_vals(self, move_lines, log_id=False):
        depreciation_date = self.env.context.get(
            'depreciation_date') or self.depreciation_date or fields.Date.context_today(
            self)
        return {
            'ref': self.asset_id.code,
            'date': depreciation_date or False,
            'journal_id': self.asset_id.category_id.journal_id.id,
            'line_ids': [(0, 0, move_line) for move_line in move_lines],
            'asset_log_id': log_id,
            'asset_id': self.asset_id.id
        }

    def get_disposal_move_lines(self):
        prec = self.env['decimal.precision'].precision_get('Account')
        company_currency = self.asset_id.company_id.currency_id
        current_currency = self.asset_id.currency_id
        depreciation_date = self.env.context.get(
            'depreciation_date') or self.depreciation_date or fields.Date.context_today(
            self)
        if self.asset_id.revaluation_line_ids:
            asset_value = self.asset_id.revaluation_line_ids.sorted(
                lambda line: line.revaluation_date, reverse=True)[0].revaluation_value
        else:
            asset_value = self.asset_id.value
        depreciated_move_lines = [move.line_ids.filtered(
            lambda line: line.account_id == self.asset_id.category_id.account_depreciation_id) for move in self.asset_id.move_ids]
        reserved_profit_move_lines = [move.line_ids.filtered(
            lambda line: line.account_id == self.asset_id.category_id.account_revaluation_equity_id) for move in self.asset_id.move_ids]
        depreciated_amount_currency = sum(move_line.credit - move_line.debit for move_line in depreciated_move_lines)
        reserved_profit_amount_currency = sum(move_line.credit - move_line.debit for move_line in reserved_profit_move_lines)
        total_amount = current_currency.with_context(
            date=depreciation_date).compute(asset_value, company_currency)
        depreciated_amount = current_currency.with_context(
            date=depreciation_date).compute(depreciated_amount_currency, company_currency)
        reserved_profit_amount = current_currency.with_context(
            date=depreciation_date).compute(reserved_profit_amount_currency,
                                            company_currency)
        amount_currency = asset_value - depreciated_amount_currency - reserved_profit_amount_currency
        amount = current_currency.with_context(
            date=depreciation_date).compute(
            amount_currency, company_currency)
        return [
            {
                'name': '{} {}/{}'.format(
                    self.asset_id.name,
                    self.sequence,
                    len(self.asset_id.depreciation_line_ids)
                ),
                'account_id': self.asset_id.category_id.account_asset_id.id,
                'debit': 0.0 if float_compare(
                    total_amount, 0.0, precision_digits=prec) > 0 else -total_amount,
                'credit': total_amount if float_compare(
                    total_amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'journal_id': self.asset_id.category_id.journal_id.id,
                'partner_id': self.asset_id.partner_id.id,
                'analytic_account_id':
                    self.asset_id.category_id.account_analytic_id.id if
                    self.asset_id.category_id.type == 'sale' else False,
                'currency_id': company_currency != current_currency and
                               current_currency.id or False,
                'amount_currency': company_currency != current_currency
                                   and - 1.0 * asset_value or 0.0,
            },
            {
                'name': '{} {}/{}'.format(
                    self.asset_id.name,
                    self.sequence,
                    len(self.asset_id.depreciation_line_ids)
                ),
                'account_id': self.asset_id.category_id.account_depreciation_id.id,
                'credit': 0.0 if float_compare(
                    depreciated_amount, 0.0, precision_digits=prec) > 0 else -depreciated_amount,
                'debit': depreciated_amount if float_compare(
                    depreciated_amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'journal_id': self.asset_id.category_id.journal_id.id,
                'partner_id': self.asset_id.partner_id.id,
                'analytic_account_id': False,
                'currency_id': company_currency != current_currency and
                               current_currency.id or False,
                'amount_currency': company_currency != current_currency
                                   and depreciated_amount_currency or 0.0,
            },
            {
                'name': '{} {}/{}'.format(
                    self.asset_id.name,
                    self.sequence,
                    len(self.asset_id.depreciation_line_ids)
                ),
                'account_id': self.asset_id.category_id.account_revaluation_equity_id.id,
                'credit': 0.0 if float_compare(
                    reserved_profit_amount, 0.0,
                    precision_digits=prec) > 0 else -reserved_profit_amount,
                'debit': reserved_profit_amount if float_compare(
                    reserved_profit_amount, 0.0,
                    precision_digits=prec) > 0 else 0.0,
                'journal_id': self.asset_id.category_id.journal_id.id,
                'partner_id': self.asset_id.partner_id.id,
                'analytic_account_id': False,
                'currency_id': company_currency != current_currency and
                               current_currency.id or False,
                'amount_currency': company_currency != current_currency
                                   and reserved_profit_amount_currency or 0.0,
            },
            {
                'name': '{} {}/{}'.format(
                    self.asset_id.name,
                    self.sequence,
                    len(self.asset_id.depreciation_line_ids)
                ),
                'account_id': self.asset_id.category_id.account_depreciation_disposal_id.id,
                'credit': 0.0 if float_compare(
                    amount, 0.0, precision_digits=prec) > 0 else -amount,
                'debit': amount if float_compare(
                    amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'journal_id': self.asset_id.category_id.journal_id.id,
                'partner_id': self.asset_id.partner_id.id,
                'analytic_account_id':
                    self.asset_id.category_id.account_analytic_id.id if
                    self.asset_id.category_id.type == 'purchase' else False,
                'currency_id': company_currency != current_currency and
                               current_currency.id or False,
                'amount_currency': company_currency != current_currency
                                   and amount_currency or 0.0,
            }
        ]

    def get_move_lines(self, accounting_date):
        prec = self.env['decimal.precision'].precision_get('Account')
        company_currency = self.asset_id.company_id.currency_id
        current_currency = self.asset_id.currency_id
        depreciation_date = accounting_date or self.env.context.get(
            'depreciation_date') or self.depreciation_date or fields.Date.context_today(
            self)
        amount = current_currency.with_context(
            date=depreciation_date).compute(
            self.period_amount + self.revaluation_period_amount,
            company_currency)
        return [
            {
                'name': '{} {}/{}'.format(
                    self.asset_id.name,
                    self.sequence,
                    len(self.asset_id.depreciation_line_ids)
                ),
                'account_id': self.asset_id.category_id.account_depreciation_id.id,
                'debit': 0.0 if float_compare(
                    amount, 0.0, precision_digits=prec) > 0 else -amount,
                'credit': amount if float_compare(
                    amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'journal_id': self.asset_id.category_id.journal_id.id,
                'partner_id': self.asset_id.partner_id.id,
                'analytic_account_id':
                    self.asset_id.category_id.account_analytic_id.id if
                    self.asset_id.category_id.type == 'sale' else False,
                'currency_id': company_currency != current_currency and
                               current_currency.id or False,
                'amount_currency': company_currency != current_currency
                                   and - 1.0 * self.amount or 0.0,
            },
            {
                'name': '{} {}/{}'.format(
                    self.asset_id.name,
                    self.sequence,
                    len(self.asset_id.depreciation_line_ids)
                ),
                'account_id': self.asset_id.category_id.account_depreciation_expense_id.id,
                'credit': 0.0 if float_compare(
                    amount, 0.0, precision_digits=prec) > 0 else -amount,
                'debit': amount if float_compare(
                    amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'journal_id': self.asset_id.category_id.journal_id.id,
                'partner_id': self.asset_id.partner_id.id,
                'analytic_account_id':
                    self.asset_id.category_id.account_analytic_id.id if
                    self.asset_id.category_id.type == 'purchase' else False,
                'currency_id': company_currency != current_currency and
                               current_currency.id or False,
                'amount_currency': company_currency != current_currency
                                   and self.amount or 0.0,
            }
        ]

    def create_grouped_move(self, post_move=True):
        if not self.exists():
            return []

        created_moves = self.env['account.move']
        category_id = self[0].asset_id.category_id
        depreciation_date = self.env.context.get(
            'depreciation_date') or fields.Date.context_today(self)
        amount = 0.0
        for line in self:
            company_currency = line.asset_id.company_id.currency_id
            current_currency = line.asset_id.currency_id
            amount += current_currency.compute(line.amount, company_currency)

        name = category_id.name + _(' (grouped)')
        move_line_1 = {
            'name': name,
            'account_id': category_id.account_depreciation_id.id,
            'debit': 0.0,
            'credit': amount,
            'journal_id': category_id.journal_id.id,
            'analytic_account_id': category_id.account_analytic_id.id if
            category_id.type == 'sale' else False,
        }
        move_line_2 = {
            'name': name,
            'account_id': category_id.account_depreciation_expense_id.id,
            'credit': 0.0,
            'debit': amount,
            'journal_id': category_id.journal_id.id,
            'analytic_account_id': category_id.account_analytic_id.id if
            category_id.type == 'purchase' else False,
        }
        move_vals = {
            'ref': category_id.name,
            'date': depreciation_date or False,
            'journal_id': category_id.journal_id.id,
            'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
            'asset_id': line.asset_id.id,
        }
        move = self.env['account.move'].create(move_vals)
        self.write({'move_id': move.id, 'move_check': True})
        created_moves |= move

        if post_move and created_moves:
            self.post_lines_and_close_asset()
            created_moves.post()
        return [x.id for x in created_moves]

    def post_lines_and_close_asset(self):
        # We re-evaluate the assets to determine whether we can close them
        for line in self:
            line.log_message_when_posted()
            asset = line.asset_id
            if asset.currency_id.is_zero(asset.value_residual):
                asset.message_post(body=_("Document closed."))
                asset.write({'state': 'close'})

    def log_message_when_posted(self):
        def _format_message(message_description, tracked_values):
            message = ''
            if message_description:
                message = '<span>%s</span>' % message_description
            for name, values in tracked_values.items():
                message += '<div> &nbsp; &nbsp; &bull; <b>%s</b>: ' % name
                message += '%s</div>' % values
            return message

        for line in self:
            if line.move_id and line.move_id.state == 'draft':
                partner_name = line.asset_id.partner_id.name
                currency_name = line.asset_id.currency_id.name
                msg_values = {_('Currency'): currency_name, _('Amount'): line.amount}
                if partner_name:
                    msg_values[_('Partner')] = partner_name
                msg = _format_message(_('Depreciation line posted.'), msg_values)
                line.asset_id.message_post(body=msg)

    def unlink(self):
        for record in self:
            if record.move_check:
                if record.asset_id.category_id.type == 'purchase':
                    msg = _("You cannot delete posted depreciation lines.")
                else:
                    msg = _("You cannot delete posted installment lines.")
                raise UserError(msg)

        return super(AccountAssetDepreciationLine, self).unlink()


class AssetDepreciationLog(models.Model):
    _name = "asset.depreciation.log"
    _description = "Asset Depreciation Log"

    def _get_date_start(self):
        return datetime.now() + relativedelta(months=-1, day=1,)

    def _get_date_end(self):
        return datetime.now() + relativedelta(day=1, days=-1)

    def _get_default_accounting_date(self):
        return datetime.now() + relativedelta(day=1, days=-1)

    name = fields.Char(
        'Name',
        required=True)
    date = fields.Date(
        'Registration Date',
        default=datetime.today())
    accounting_date = fields.Date(
        'Accounting Date',
        default=_get_default_accounting_date,
        help="If empty, accounting date will be taken from depreciation board"
    )
    asset_ids = fields.Many2many(
        'account.asset.asset',
        'asset_log_rel',
        'log_id',
        'asset_id',
        string='Assets')
    move_ids = fields.One2many(
        'account.move',
        'asset_log_id',
        'Moves',
        readonly=True)
    date_start = fields.Date(
        'Start Date',
        default=_get_date_start)
    date_end = fields.Date(
        'End Date',
        default=_get_date_end)
    category_ids = fields.Many2many(
        'account.asset.category',
        'asset_dok_category_ref',
        'log_id',
        'category_id',
        string='Asset category')
    state = fields.Selection(
        [('draft', 'New'), ('done', 'Done')],
        'State',
        readonly=True,
        default='draft')

    def asset_compute(self):
        ass_obj = self.env['account.asset.asset']
        asset_filter = [('state', '=', 'open')]
        created_moves = []
        if self.category_ids:
            asset_filter.append(
                ('category_id', 'in', tuple(
                    [category.id for category in self.category_ids])))
            asset_ids = ass_obj.search(asset_filter)
        elif self.asset_ids:
            asset_ids = self.asset_ids
        else:
            asset_ids = ass_obj.search(asset_filter)
        for asset in asset_ids:
            created_moves += asset._compute_entries(
                self.date_end, self.date_start, self.id, self.accounting_date)
        return self.write({'state': 'done', 'move_ids': [(6, 0, created_moves)]})

    def button_cancel(self):
        depreciation_lin_obj = self.env['account.asset.depreciation.line']
        depreciation_lines = depreciation_lin_obj.search([
            ('move_id', 'in', tuple([move.id for move in self.move_ids]))])
        depreciation_lines.write({'move_id': False})
        self.move_ids.button_draft()
        self.move_ids.button_cancel()
        return self.write({'state': 'draft'})

    def unlink(self):
        if self.state == 'done':
            raise UserError(_('Warning!'),
                                 _('Cannot unlink a log in done state!'))
        super(AssetDepreciationLog, self).unlink()
        return True


class AccountMove(models.Model):
    _inherit = "account.move"

    asset_log_id = fields.Many2one(
        'asset.depreciation.log',
        'Asset depreciation log')
    asset_id = fields.Many2one(
        'account.asset.asset',
        'Asset',
        help="Asset from which move entry has been generated",
        readonly=True,
        states={'draft': [('readonly', False)]})


class AssetRevaluationLog(models.Model):
    _name = "asset.revaluation.log"
    _description = "Asset Revaluation Log"

    name = fields.Char(
        'Name',
        required=True)
    date = fields.Date(
        'Registration date',
        default=datetime.today())
    revaluation_date = fields.Date(
        'Asset Revaluation Date',
        default=datetime.today())
    asset_id = fields.Many2one(
        'account.asset.asset',
        string='Asset',
        required=True,
        ondelete='cascade')
    currency_id = fields.Many2one(
        'res.currency',
        related='asset_id.currency_id',
        string='Currency')
    net_value = fields.Monetary(
        string='Net Asset Value',
    )
    revaluation_value = fields.Monetary(
        string='Asset Revaluation Value',
    )
    difference_value = fields.Monetary(
        string='Difference Value',
    )
    user_id = fields.Many2one(
        'res.users', 'User',
        default=lambda self: self.env.user,
        index=True, required=True)
    note = fields.Text(string='Notes')
