
from odoo import api, fields, models, _,exceptions
import re
import logging

_logger = logging.getLogger(__name__)

class CompanyVatCheck(models.TransientModel):
	_name = 'company.vat.check.number'
	_description = 'VAT Check'

	@api.model
	def _get_default_hmrc_config_id(self):
	    return self.env['mtd.vat_hmrc_configuration'].search([],limit=1)

	company_type = fields.Selection(
		string='Endpoint Type',
		selection=[('company', 'Company'), ('business', 'Business')],
		default='company'
	)
	hmrc_configuration = fields.Many2one(comodel_name="mtd.vat_hmrc_configuration", string="HMRC Configuration", default=_get_default_hmrc_config_id)
	path = fields.Char(string="sandbox_url")
	company_id = fields.Many2one(comodel_name="res.company", string="Company", default=lambda self: self.env['res.company']._company_default_get('account.account'))
	vrn = fields.Char(related="company_id.vat", string="VAT Number", readonly=True)

	def get_vrn(self, vrn):
		# strip any space
		strip_vrn = vrn.replace(" ", "")
		split_vrn = re.findall('\d+|\D+', vrn)
		return split_vrn[len(split_vrn) - 1]

	def check_vat_number(self):
		partner_id = self.env['res.partner'].browse(self._context.get('active_id'))
		path = ''
		if self.company_type == 'company':
			self.path = '/organisations/vat/check-vat-number/lookup/{targetVrn}'.format(targetVrn=self.get_vrn(partner_id.vat))
		else:
			company = self.env['res.company']._company_default_get('account.account')
			if not company.vat:
				raise exceptions.Warning(
				    "Please Configure Company Vat Number For Business Vat Check !!"
				)
			self.path = '/organisations/vat/check-vat-number/lookup/{targetVrn}/{requesterVrn}'.format(
				targetVrn=self.get_vrn(partner_id.vat),
				requesterVrn=self.get_vrn(company.vat)
			)
		if self.hmrc_configuration:
			version = self.env['mtd.vat_check_endpoint'].json_command(self._name, self.id, partner_id)
		else:
			account_mtd = self.env['ir.module.module'].search([('name', '=', 'account_mtd')])
			if account_mtd and account_mtd.state == 'installed':
				mtd_config = self.env['mtd.hmrc_configuration'].search([], limit=1)
				hmrc_config = {
					'name': mtd_config.name,
					'client_id': mtd_config.client_id,
					'client_secret': mtd_config.client_secret,
					'environment': mtd_config.environment,
					'hmrc_url': mtd_config.hmrc_url,
					'access_token': mtd_config.access_token,
					'refresh_token': mtd_config.refresh_token,
					'state': mtd_config.state,
				}
				self.hmrc_configuration = self.env['mtd.vat_hmrc_configuration'].create(hmrc_config)
				version = self.env['mtd.vat_check_endpoint'].json_command(self._name, self.id, partner_id)
			else:
				raise exceptions.Warning(
				    "HMRC Setup is not Configure!!!\n " +
				    "Please Provide Configuration Details"
				)
		return True
