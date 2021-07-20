from odoo import fields, models
from odoo.tools.safe_eval import safe_eval


class AccountTaxTemplateMargin(models.Model):
    _inherit = "account.tax.template"

    amount_type = fields.Selection(
        ondelete={
            "margin": "cascade",
        },
        selection_add=[("margin", "Margin")],
    )


class AccountTaxMargin(models.Model):
    _inherit = "account.tax"

    amount_type = fields.Selection(
        ondelete={
            "margin": "cascade",
        },
        selection_add=[("margin", "Margin")],
    )

    def _compute_amount(
        self, base_amount, price_unit, quantity=1.0, product=None, partner=None
    ):
        self.ensure_one()
        if self.amount_type == "margin":
            price_include = self.price_include
            if product and product._name == "product.template":
                product = product.product_variant_id
            company = self.env.company
            localdict = {
                "base_amount": base_amount,
                "price_unit": price_unit,
                "quantity": quantity,
                "product": product,
                "partner": partner,
                "company": company,
            }
            if not price_include:
                if product:
                    safe_eval(
                        "result = (base_amount - product.standard_price ) * {}".format(
                            self.amount / 100.0
                        ),
                        localdict,
                        mode="exec",
                        nocopy=True,
                    )
                    return localdict["result"] if localdict["result"] > 0 else 0

                else:
                    res = (
                        super(AccountTaxMargin, self)._compute_amount(
                            base_amount, price_unit, quantity, product, partner
                        )
                        or 0.0
                    )
            else:
                if product:
                    safe_eval(
                        "result = (base_amount - product.standard_price) - "
                        "(base_amount - product.standard_price ) / (1 + {})".format(
                            self.amount / 100.0
                        ),
                        localdict,
                        mode="exec",
                        nocopy=True,
                    )
                    return localdict["result"] if localdict["result"] > 0 else 0
                else:
                    res = (
                        super(AccountTaxMargin, self)._compute_amount(
                            base_amount, price_unit, quantity, product, partner
                        )
                        or 0.0
                    )
        else:
            res = super(AccountTaxMargin, self)._compute_amount(
                base_amount, price_unit, quantity, product, partner
            )
        return res

    def compute_all(
        self,
        price_unit,
        currency=None,
        quantity=1.0,
        product=None,
        partner=None,
        is_refund=False,
        handle_price_include=True,
    ):
        taxes = self.filtered(lambda r: r.amount_type != "margin")
        company = self.env.company
        if product and product._name == "product.template":
            product = product.product_variant_id
        for tax in self.filtered(lambda r: r.amount_type == "margin"):
            localdict = self._context.get("tax_computation_context", {})
            localdict.update(
                {
                    "price_unit": price_unit,
                    "quantity": quantity,
                    "product": product,
                    "partner": partner,
                    "company": company,
                }
            )
            safe_eval("result = True", localdict, mode="exec", nocopy=True)
            if localdict.get("result", False):
                taxes += tax
        res = super(AccountTaxMargin, taxes).compute_all(
            price_unit,
            currency,
            quantity,
            product,
            partner,
            is_refund=is_refund,
            handle_price_include=handle_price_include,
        )
        if len(res["taxes"]) > 1:
            return res
        else:
            total_res = {}
            total_res["base_tags"] = res["base_tags"]
            total_res["taxes"] = []
            total_base = 0
            total_tax = 0
            for lst_taxes in res["taxes"]:
                if lst_taxes.get("price_include"):
                    lst_taxes.update(
                        {"base": price_unit * quantity - lst_taxes["amount"]}
                    )
                total_res["taxes"].append(lst_taxes)
                total_base += lst_taxes["base"]
                total_tax += lst_taxes["amount"]
            # If no taxes are present, we should fallback to res values
            # rather than arbitrarily leaving total_base and total_tax at 0
            if not res["taxes"]:
                total_base = res.get("total_excluded", 0.00)
                total_tax = 0
            total_res["total_included"] = total_base + total_tax
            total_res["total_excluded"] = total_base
            total_res["total_void"] = total_base + total_tax
            return total_res
