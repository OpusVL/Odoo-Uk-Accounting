# -*- coding: utf-8 -*-

from odoo import models
from odoo.addons.approval_hierarchy import helpers


class IrModelField(models.Model):
    _inherit = 'ir.model.fields'

    def _reflect_field_params(self, field):
        """ Tracking value can be either a boolean enabling tracking mechanism
        on field, either an integer giving the sequence. Default sequence is
        set to 100. """
        vals = super(IrModelField, self)._reflect_field_params(field)
        model = self.env['ir.model']._get(field.model_name)
        fields_to_be_tracked = helpers.get_fields_to_be_tracked()
        if model.model in fields_to_be_tracked and \
                vals.get('name') in fields_to_be_tracked.get(model.model):
            vals.update({
                'tracking': 100}
            )
        return vals
