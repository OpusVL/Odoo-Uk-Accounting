# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.addons.approval_hierarchy import helpers
from odoo.addons.approval_hierarchy.helpers import CUSTOM_ERROR_MESSAGES, CONFIGURATION_ERROR_MESSAGE, MOVE_TYPE_MAPPING
from odoo.exceptions import UserError


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def write(self, vals):
        fields_to_be_skipped = helpers.get_fields_to_be_excluded()
        model_access_rights = helpers.get_create_write_unlink_access_groups()
        if fields_to_be_skipped.get(
                self._name) and any(
            field in vals for field in fields_to_be_skipped.get(
                self._name)):
            return super(BaseModel, self).write(vals)
        if self.env.user.is_superuser():
            return super(BaseModel, self).write(vals)
        if self._context.get('supplier_action'):
            return super(BaseModel, self).write(vals)
        if self._name in model_access_rights and (
                not self.env.user.employee_id or
                not self.env.user.employee_id.job_id):
            raise UserError(CONFIGURATION_ERROR_MESSAGE)
        if self._name == 'account.move':
            if not self.env.user.employee_id or not self.env.user.employee_id.job_id:
                raise UserError(CONFIGURATION_ERROR_MESSAGE)
            for move in self:
                if not self.env.user.has_group(
                        model_access_rights.get('{}.{}'.format(
                            self._name, move.type))):
                    raise UserError(
                        CUSTOM_ERROR_MESSAGES.get('write') % MOVE_TYPE_MAPPING.get(
                            move.type))
        elif self._name == 'hr.employee':
            if self._context.get('from_my_profile') and \
                    self.env.user == self.user_id:
                return super(BaseModel, self).write(vals)
        if self._name in model_access_rights:
            if not self.env.user.has_group(
                    model_access_rights.get(self._name)):
                raise UserError(
                    CUSTOM_ERROR_MESSAGES.get('write') % self._description)
        return super(BaseModel, self).write(vals)

    def unlink(self):
        if self.env.user.is_superuser():
            return super(BaseModel, self).unlink()
        model_access_rights = helpers.get_create_write_unlink_access_groups()
        if self._name in model_access_rights:
            if not self.env.user.has_group(
                    model_access_rights.get(self._name)):
                raise UserError(
                    CUSTOM_ERROR_MESSAGES.get('unlink') % self._description)
        if self._name == 'account.move':
            for move in self:
                if not self.env.user.has_group(
                        model_access_rights.get('{}.{}'.format(
                            self._name, move.type))):
                    raise UserError(
                        CUSTOM_ERROR_MESSAGES.get('unlink') % MOVE_TYPE_MAPPING.get(
                            move.type))
        return super(BaseModel, self).unlink()

    @api.model_create_multi
    def create(self, vals_list):
        results = super(BaseModel, self).create(vals_list)
        if self.env.user.is_superuser():
            return results
        model_access_rights = helpers.get_create_write_unlink_access_groups()
        if self._name in model_access_rights:
            if not self.env.user.has_group(
                    model_access_rights.get(self._name)):
                raise UserError(
                    CUSTOM_ERROR_MESSAGES.get('create') % self._description)
        if self._name == 'account.move':
            for move in results:
                if not self.env.user.has_group(
                        model_access_rights.get('{}.{}'.format(
                            self._name, move.type))):
                    raise UserError(
                        CUSTOM_ERROR_MESSAGES.get('create') % MOVE_TYPE_MAPPING.get(
                            move.type))
        return results
