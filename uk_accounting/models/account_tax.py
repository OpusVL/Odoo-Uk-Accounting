# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class AccountTaxTemplateMargin(models.Model):
    _inherit = "account.tax.template"

    amount_type = fields.Selection(selection_add=[('margin', 'Margin')])


class AccountTaxMargin(models.Model):
    _inherit = "account.tax"

    amount_type = fields.Selection(selection_add=[('margin', 'Margin')])

    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
        self.ensure_one()
        if product and product._name == 'product.template':
            product = product.product_variant_id
        if self.amount_type == 'margin':
            company = self.env.company
            localdict = {'base_amount': base_amount, 'price_unit': price_unit, 'quantity': quantity, 'product': product,
                         'partner': partner, 'company': company}
            safe_eval('result = (price_unit - product.standard_price ) * {}'.format(self.amount/100.0),
                      localdict, mode="exec", nocopy=True)
            return localdict['result']
        return super(AccountTaxMargin, self)._compute_amount(base_amount, price_unit, quantity, product, partner)

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None,
                    is_refund=False, handle_price_include=True):
        taxes = self.filtered(lambda r: r.amount_type != 'margin')
        company = self.env.company
        if product and product._name == 'product.template':
            product = product.product_variant_id
        for tax in self.filtered(lambda r: r.amount_type == 'margin'):
            localdict = self._context.get('tax_computation_context', {})
            localdict.update({'price_unit': price_unit, 'quantity': quantity, 'product': product,
                              'partner': partner, 'company': company})
            safe_eval('result = True', localdict, mode="exec", nocopy=True)
            if localdict.get('result', False):
                taxes += tax
        return super(AccountTaxMargin, taxes).compute_all(price_unit, currency, quantity, product, partner,
                                                          is_refund=is_refund, handle_price_include=handle_price_include)
