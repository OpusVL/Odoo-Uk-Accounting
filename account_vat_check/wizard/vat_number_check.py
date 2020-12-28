
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
	is_business = fields.Boolean(string='Select if you want proof of your check (for UK VAT-registered businesses only)')
	hmrc_configuration = fields.Many2one(comodel_name="mtd.vat_hmrc_configuration", string="HMRC Configuration", default=_get_default_hmrc_config_id)
	path = fields.Char(string="sandbox_url")
	company_id = fields.Many2one(comodel_name="res.company", string="Company", default=lambda self: self.env.company)
	vrn = fields.Char(related="company_id.vat", string="VAT Number", readonly=True)

	@api.onchange('is_business')
	def _onchange_is_business(self):
		if self.is_business:
			self.company_type = 'business'
		else:
			self.company_type = 'company'

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
			if not self.env.company.vat:
				raise exceptions.Warning(
				    "Please Configure Company Vat Number For Business Vat Check !!"
				)
			self.path = '/organisations/vat/check-vat-number/lookup/{targetVrn}/{requesterVrn}'.format(
				targetVrn=self.get_vrn(partner_id.vat),
				requesterVrn=self.get_vrn(self.env.company.vat)
			)
		if self.hmrc_configuration:
			version = self.env['mtd.vat_check_endpoint'].json_command(self._name, self.id, partner_id)
		else:
			raise exceptions.Warning(
			    "HMRC Setup is not Configure!!!\n " +
			    "Please Provide Configuration Details"
			)
		return True
