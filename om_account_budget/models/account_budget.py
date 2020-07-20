# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

# ---------------------------------------------------------
# Budgets
# ---------------------------------------------------------
class AccountBudgetPost(models.Model):
    _name = "account.budget.post"
    _order = "name"
    _description = "Budgetary Position"

    name = fields.Char('Name', required=True)
    account_ids = fields.Many2many('account.account', 'account_budget_rel', 'budget_id', 'account_id', 'Accounts',
        domain=[('deprecated', '=', False)])
    company_id = fields.Many2one('res.company', 'Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get('account.budget.post'))

    def _check_account_ids(self, vals):
        # Raise an error to prevent the account.budget.post to have not specified account_ids.
        # This check is done on create because require=True doesn't work on Many2many fields.
        if 'account_ids' in vals:
            account_ids = self.resolve_2many_commands('account_ids', vals['account_ids'])
        else:
            account_ids = self.account_ids
        if not account_ids:
            raise ValidationError(_('The budget must have at least one account.'))

    @api.model
    def create(self, vals):
        self._check_account_ids(vals)
        return super(AccountBudgetPost, self).create(vals)

    
    def write(self, vals):
        self._check_account_ids(vals)
        return super(AccountBudgetPost, self).write(vals)


class CrossoveredBudget(models.Model):
    _name = "crossovered.budget"
    _description = "Budget"
    _inherit = ['mail.thread']

    name = fields.Char('Budget Name', required=True, states={'done': [('readonly', True)]})
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user, oldname='creating_user_id')
    date_from = fields.Date('Start Date', required=True, states={'done': [('readonly', True)]})
    date_to = fields.Date('End Date', required=True, states={'done': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'Confirmed'),
        ('validate', 'Validated'),
        ('done', 'Done')
        ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, track_visibility='always')
    crossovered_budget_line = fields.One2many('crossovered.budget.lines', 'crossovered_budget_id', 'Budget Lines',
        states={'done': [('readonly', True)]}, copy=True)
    company_id = fields.Many2one('res.company', 'Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get('account.budget.post'))

    
    def action_budget_confirm(self):
        self.write({'state': 'confirm'})

    
    def action_budget_draft(self):
        self.write({'state': 'draft'})

    
    def action_budget_validate(self):
        self.write({'state': 'validate'})

    
    def action_budget_cancel(self):
        self.write({'state': 'cancel'})

    
    def action_budget_done(self):
        self.write({'state': 'done'})


class CrossoveredBudgetLines(models.Model):
    _name = "crossovered.budget.lines"
    _description = "Budget Line"

    name = fields.Char(compute='_compute_line_name')
    crossovered_budget_id = fields.Many2one('crossovered.budget', 'Budget', ondelete='cascade', index=True, required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    analytic_group_id = fields.Many2one('account.analytic.group', 'Analytic Group', related='analytic_account_id.group_id', readonly=True)
    general_budget_id = fields.Many2one('account.budget.post', 'Budgetary Position')
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    paid_date = fields.Date('Paid Date')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    planned_amount = fields.Monetary(
        'Budget',
        required=True,
        help="Amount you plan to earn/spend. Record a positive amount if it is a revenue and a negative amount if it is a cost.",
    )
    computed_practical_amount = fields.Monetary(
        compute='_compute_practical_amount',
        string='Computed Practical Amount',
        help="Amount really earned/spent.",
    )
    practical_amount = fields.Monetary(
        string='Actual',
        help="Amount really earned/spent.",
    )
    difference_amount = fields.Monetary(string='Variance')
    company_id = fields.Many2one(
        related='crossovered_budget_id.company_id',
        comodel_name='res.company',
        string='Company',
        store=True,
        readonly=True,
    )
    crossovered_budget_state = fields.Selection(
        related='crossovered_budget_id.state',
        string='Budget State',
        store=True,
        readonly=True,
    )

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        # overrides the default read_group in order to compute the computed fields manually for the group

        result = super(CrossoveredBudgetLines, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                                orderby=orderby, lazy=lazy)
        fields_list = ['practical_amount']
        if any(x in fields for x in fields_list):
            for group_line in result:

                # initialise fields to compute to 0 if they are requested
                if 'practical_amount' in fields:
                    group_line['practical_amount'] = 0

                if group_line.get('__domain'):
                    all_budget_lines_that_compose_group = self.search(group_line['__domain'])
                else:
                    all_budget_lines_that_compose_group = self.search([])
                for budget_line_of_group in all_budget_lines_that_compose_group:
                    if 'practical_amount' in fields:
                        group_line['practical_amount'] += budget_line_of_group.practical_amount
        return result

    def _compute_line_name(self):
        #just in case someone opens the budget line in form view
        computed_name = self.crossovered_budget_id.name
        if self.general_budget_id:
            computed_name += ' - ' + self.general_budget_id.name
        if self.analytic_account_id:
            computed_name += ' - ' + self.analytic_account_id.name
        self.name = computed_name

    
    def _compute_practical_amount(self):
        for line in self:
            acc_ids = line.general_budget_id.account_ids.ids
            date_to = line.date_to
            date_from = line.date_from
            if line.analytic_account_id.id:
                analytic_line_obj = self.env['account.analytic.line']
                domain = [('account_id', '=', line.analytic_account_id.id),
                          ('date', '>=', date_from),
                          ('date', '<=', date_to),
                          ]
                if acc_ids:
                    domain += [('general_account_id', 'in', acc_ids)]

                where_query = analytic_line_obj._where_calc(domain)
                analytic_line_obj._apply_ir_rules(where_query, 'read')
                from_clause, where_clause, where_clause_params = where_query.get_sql()
                select = "SELECT SUM(amount) from " + from_clause + " where " + where_clause

            else:
                aml_obj = self.env['account.move.line']
                domain = [('account_id', 'in',
                           line.general_budget_id.account_ids.ids),
                          ('date', '>=', date_from),
                          ('date', '<=', date_to)
                          ]
                where_query = aml_obj._where_calc(domain)
                aml_obj._apply_ir_rules(where_query, 'read')
                from_clause, where_clause, where_clause_params = where_query.get_sql()
                select = "SELECT sum(credit)-sum(debit) from " + from_clause + " where " + where_clause

            self.env.cr.execute(select, where_clause_params)
            actual_amount = self.env.cr.fetchone()[0] or 0.0
            line.write({
                'practical_amount': actual_amount,
                'difference_amount': actual_amount - line.planned_amount,
            })
            line.computed_practical_amount = actual_amount
            # I saw this write() and auxiliary computed field, and tried to switch to
            # stored-computed fields for the practical_amount and difference_amount,
            # not understanding why this hack existed.
            # That prevented the values from updating when journal entries were
            # posted.
            # I'm not totally sure how this works still, but I suspect it's down to
            # the non-stored computed_practical_amount being recomputed each time
            # it is requested and forcing this write() to happen and store the values.
            # This means when you want the up to date planned_amount or
            # actual_amount, you must also request the computed_practical_amount,
            # even if you just throw it away or make it invisible.
            # If we wanted to query it with SQL, we might find it's sensible to
            # have a cron job run this method every so often.
            # DEBT: This is an extra burden on anybody calling this code, and we
            #  should make the effort to turn it into a proper stored computed field,
            #  with appropriate @api.depends(...) clauses (which, I realise, will be
            #  a bit more involved than normal to construct).  Unless, that is,
            #  having them as stored-computed fields would be a performance burden.

    @api.constrains('general_budget_id', 'analytic_account_id')
    def _must_have_analytical_or_budgetary_or_both(self):
        if not self.analytic_account_id and not self.general_budget_id:
            raise ValidationError(
                _("You have to enter at least a budgetary position or analytic account on a budget line."))

    
    def action_open_budget_entries(self):
        if self.analytic_account_id:
            # if there is an analytic account, then the analytic items are loaded
            action = self.env['ir.actions.act_window'].for_xml_id('analytic', 'account_analytic_line_action_entries')
            action['domain'] = [('account_id', '=', self.analytic_account_id.id),
                                ('date', '>=', self.date_from),
                                ('date', '<=', self.date_to)
                                ]
            if self.general_budget_id:
                action['domain'] += [('general_account_id', 'in', self.general_budget_id.account_ids.ids)]
        else:
            # otherwise the journal entries booked on the accounts of the budgetary postition are opened
            action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_account_moves_all_a')
            action['domain'] = [('account_id', 'in',
                                 self.general_budget_id.account_ids.ids),
                                ('date', '>=', self.date_from),
                                ('date', '<=', self.date_to)
                                ]
        return action

    @api.constrains('date_from', 'date_to')
    def _line_dates_between_budget_dates(self):
        for budget_line in self:
            budget_date_from = budget_line.crossovered_budget_id.date_from
            budget_date_to = budget_line.crossovered_budget_id.date_to
            if budget_line.date_from:
                date_from = budget_line.date_from
                if date_from < budget_date_from or date_from > budget_date_to:
                    raise ValidationError(_(
                        '"Start Date" of the budget line should be included in '
                        'the Period of the budget'))

            if budget_line.date_to:
                date_to = budget_line.date_to
                if date_to < budget_date_from or date_to > budget_date_to:
                    raise ValidationError(_(
                        '"End Date" of the budget line should be included in '
                        'the Period of the budget'))
