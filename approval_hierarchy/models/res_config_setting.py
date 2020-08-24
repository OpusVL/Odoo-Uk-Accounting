from odoo import models, api


class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'
    
    @api.model
    def set_approval_config(self):
        if self._needs_to_run():
            self._set_approval_config()
            self._update_config_parameter()

    def _set_approval_config(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'hr.hr_employee_self_edit', True)

    def _update_config_parameter(self):
        conf_param_obj = self.env['ir.config_parameter']
        conf_param_obj.set_param('has_run_approval_set_config', 'True')

    def _needs_to_run(self):
        """
        Determines whether the config setup needs to run based
            on a config parameter.
        Will create config parameter if it does not exist.
        This means we can re-run the config setup by setting the config
            parameter back to false
        """
        conf_param_obj = self.env['ir.config_parameter']
        has_run_approval_set_config_param = conf_param_obj.get_param(
            'has_run_approval_set_config')
        if has_run_approval_set_config_param is not None:
            if has_run_approval_set_config_param == 'True':
                return False
            else:
                return True
        # If the parameter doesn't exist yet, create it
        conf_param_obj.set_param('has_run_approval_set_config_param', 'False')
        return True



