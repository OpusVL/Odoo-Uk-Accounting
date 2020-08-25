# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _default_category(self):
        return self.env['res.partner.category'].browse(
            self._context.get('category_id'))

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("waiting", "Awaiting Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        tracking=True,
    )
    approval_user_id = fields.Many2one(
        'res.users',
        string='Approved by',
        tracking=True,
    )
    current_user = fields.Boolean(compute='_get_current_user')
    name = fields.Char(index=True, tracking=True,)
    # company_type is only an interface field, do not use it in business logic
    company_type = fields.Selection(
        string='Company Type',
        selection=[('person', 'Individual'), ('company', 'Company')],
        compute='_compute_company_type',
        inverse='_write_company_type',
        tracking=True,
    )
    street = fields.Char(tracking=True,)
    street2 = fields.Char(tracking=True,)
    zip = fields.Char(change_default=True, tracking=True,)
    city = fields.Char(tracking=True,)
    state_id = fields.Many2one(
        "res.country.state",
        string='State',
        ondelete='restrict',
        domain="[('country_id', '=?', country_id)]",
        tracking=True,
    )
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        ondelete='restrict',
        tracking=True,
    )
    vat = fields.Char(
        string='Tax ID',
        help="The Tax Identification Number. Complete it if the contact is "
             "subjected to government taxes. Used in some legal statements.",
        tracking=True,
    )
    phone = fields.Char(tracking=True,)
    mobile = fields.Char(tracking=True,)
    email = fields.Char(tracking=True,)
    website = fields.Char('Website Link', tracking=True,)
    category_id = fields.Many2many(
        'res.partner.category',
        column1='partner_id',
        column2='category_id',
        string='Tags',
        default=_default_category,
        tracking=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        help='The internal user in charge of this contact.',
        tracking=True,
    )
    industry_id = fields.Many2one(
        'res.partner.industry',
        'Industry',
        tracking=True,
    )
    ref = fields.Char(
        string='Reference',
        index=True,
        tracking=True,
    )
    comment = fields.Text(string='Notes', tracking=True,)
    property_supplier_payment_term_id = fields.Many2one(
        'account.payment.term',
        company_dependent=True,
        string='Vendor Payment Terms',
        help="This payment term will be used instead of the default one for "
             "purchase orders and vendor bills",
        tracking=True,
    )
    property_payment_term_id = fields.Many2one(
        'account.payment.term',
        company_dependent=True,
        string='Customer Payment Terms',
        help="This payment term will be used instead of the default one for "
             "sales orders and customer invoices",
        tracking=True,
    )
    property_account_position_id = fields.Many2one(
        'account.fiscal.position',
        company_dependent=True,
        string="Fiscal Position",
        help="The fiscal position determines the taxes/accounts used for "
             "this contact.",
        tracking=True,
    )
    property_stock_customer = fields.Many2one(
        'stock.location',
        string="Customer Location",
        company_dependent=True,
        check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', allowed_company_ids[0])]",
        help="The stock location used as destination when sending goods to this contact.",
        tracking=True,
    )
    property_stock_supplier = fields.Many2one(
        'stock.location',
        string="Vendor Location",
        company_dependent=True,
        check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', allowed_company_ids[0])]",
        help="The stock location used as source when receiving goods from this contact.",
        tracking=True,
    )
    property_account_payable_id = fields.Many2one(
        'account.account',
        company_dependent=True,
        string="Account Payable",
        domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as "
             "the payable account for the current partner",
        required=True,
        tracking=True,
    )
    property_account_receivable_id = fields.Many2one(
        'account.account',
        company_dependent=True,
        string="Account Receivable",
        domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the "
             "receivable account for the current partner",
        required=True,
        tracking=True,
    )

    def _get_current_user(self):
        for rec in self:
            rec.current_user = rec.approval_user_id == self.env.user

    @api.depends('is_company')
    def _compute_company_type(self):
        for partner in self:
            partner.company_type = 'company' if partner.is_company else 'person'

    def _write_company_type(self):
        for partner in self:
            partner.is_company = partner.company_type == 'company'

    def request_approval(self):
        role_action = self.env.ref('approval_hierarchy.supplier_approval_role')
        approved_user = self.env.user.employee_id and \
                        self.env.user.employee_id.get_approved_user(
                            role_action) or False
        if approved_user == self.env.user:
            records = self | self.child_ids.filtered(
                lambda child: child.state == 'draft')
            records.with_context(supplier_action=True).write(
                {
                    'state': 'waiting',
                    'approval_user_id': approved_user.id,
                }
            )
            self.action_approve()
        else:
            records = self | self.child_ids.filtered(
                lambda child: child.state == 'draft')
            records.with_context(supplier_action=True).write(
                {
                    'state': 'waiting',
                    'approval_user_id': approved_user and approved_user.id,
                }
            )
            return True

    def action_approve(self):
        records = self | self.child_ids.filtered(
            lambda child: child.state != 'done')
        records.with_context(supplier_action=True).write(
            {'state': 'approved'}
        )
        return True

    def action_reject(self):
        records = self | self.child_ids
        records.with_context(supplier_action=True).write(
            {'state': 'rejected'}
        )
        return True

    def action_approve_administrator(self):
        records = self | self.child_ids.filtered(
            lambda r: r.state != 'done'
        )
        records.with_context(supplier_action=True).write(
            {'state': 'approved'}
        )
        return True

    def action_reject_administrator(self):
        records = self | self.child_ids
        records.with_context(supplier_action=True).write(
            {'state': 'rejected'}
        )
        return True

    def set_to_draft(self):
        return self.with_context(supplier_action=True).write(
            {
                'state': 'draft',
                'approval_user_id': False,
             }
        )

    @api.model
    def create(self, vals):
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(_('Your configuration are not correct, '
                              'Please contact with an administrator.'))
        role_action = self.env.ref('approval_hierarchy.supplier_set_up_role')
        if not self.env.user.employee_id.check_if_has_approval_rights(
                role_action):
            raise UserError(_('You dont have rights to create a partner, '
                              'Please contact with an administrator.'))
        res = super(ResPartner, self).create(vals)
        if vals and vals.get('parent_id'):
            message = "Contact {} has been created. ".format(
                res.name)
            res.parent_id.set_to_draft()
            res.parent_id.message_post(body=message)
        return res

    def write(self, vals):
        if self._context.get('supplier_action'):
            return super(ResPartner, self.with_context(
                supplier_action=True)).write(vals)
        else:
            if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
                raise UserError(_('Your configuration are not right, '
                                  'Please contact with an administrator.'))
            role_action = self.env.ref(
                'approval_hierarchy.supplier_set_up_role')
            if not self.env.user.employee_id.check_if_has_approval_rights(
                    role_action):
                raise UserError(_('You dont have rights to modify a partner, '
                                  'Please contact with an administrator.'))
            if 'child_ids' in vals:
                for child in vals.get('child_ids'):
                    if isinstance(child, tuple) and len(child) == 3 \
                            and isinstance(child[2], dict):
                        child[2].update({
                            'state': 'draft',
                            'approval_user_id': False,
                        })
                        message = "Contact {} has been modified.".format(
                            self.browse(child[1]).name)
                        self.message_post(body=message)
            vals['state'] = 'draft'
            vals['approval_user_id'] = False
            return super(ResPartner,  self.with_context(
                supplier_action=True)).write(vals)

    def unlink(self):
        if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
            raise UserError(_('Your configuration are not right, '
                              'Please contact with an administrator.'))
        role_action = self.env.ref('approval_hierarchy.supplier_set_up_role')
        if not self.env.user.employee_id.check_if_has_approval_rights(
                role_action):
            raise UserError(_('You dont have rights to delete a partner, '
                              'Please contact with an administrator.'))
        for partner in self:
            if partner.state != 'draft':
                raise UserError(_('In order to delete a partner, '
                                  'you must set it first to draft.'))
            if partner.parent_id:
                message = "Contact {} has been deleted.".format(
                    partner.name)
                partner.parent_id.message_post(body=message)
                partner.parent_id.set_to_draft()
        return super(ResPartner, self).unlink()


class ResPartnerBank(models.Model):
    _name = 'res.partner.bank'
    _inherit = ['res.partner.bank', 'mail.thread', 'mail.activity.mixin']

    acc_number = fields.Char(
        'Account Number',
        required=True,
        tracking=True,
    )
    acc_type = fields.Selection(
        selection=lambda x: x.env['res.partner.bank'].get_supported_account_types(),
        compute='_compute_acc_type',
        string='Type',
        help='Bank account type: Normal or IBAN. '
             'Inferred from the bank account number.',
        tracking=True,
    )
    bank_id = fields.Many2one(
        'res.bank',
        string='Bank',
        tracking=True,
    )
    acc_holder_name = fields.Char(
        string='Account Holder Name',
        help="Account holder name, in case it is different "
             "than the name of the Account Holder",
        tracking=True,
    )
    sort_code = fields.Char(tracking=True,)
    short_name = fields.Char(tracking=True,)

    @api.model
    def create(self, vals):
        res = super(ResPartnerBank, self).create(vals)
        if vals:
            message = "Bank Account {} has been created. " \
                      "View accounts detail for more information".format(
                res.acc_number)
            res.partner_id.message_post(body=message)
        return res

    def unlink(self):
        for bank_account in self:
            message = "Bank Account {} has been deleted.".format(
                bank_account.acc_number)
            bank_account.partner_id.message_post(body=message)
        return super(ResPartnerBank, self).unlink()

    def write(self, vals):
        res = super(ResPartnerBank, self).write(vals)
        message = False
        if 'acc_number' in vals:
            message = "Bank Account {} has been modified. " \
                      "View accounts detail for more information".format(
                vals.get('acc_number'))
        elif len(vals) != 1 and 'partner_id' not in vals:
            message = "Bank Account {} has been modified. " \
                      "View accounts detail for more information".format(
                self.acc_number)
        if message:
            self.partner_id.message_post(body=message)
        return res
