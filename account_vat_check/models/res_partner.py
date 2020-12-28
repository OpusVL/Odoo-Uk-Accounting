from openerp import models, fields, api, _,exceptions
from datetime import datetime, timedelta
import re

class ResPartner(models.Model):
	_inherit = 'res.partner'

	response_from_hmrc = fields.Text(string="Response From HMRC", readonly=True)
	vat = fields.Char('TIN')

	@api.multi
	def check_uk_vat(self):
		""" Check Uk Vat Number """
		if self.vat:
			strip_vrn = self.vat.replace(" ", "")
			split_vrn = re.findall('\d+|\D+', self.vat)
			if split_vrn and len(split_vrn[len(split_vrn)-1]) in [9,12]:
				action = self.env.ref('account_vat_check.action_vat_number_check_view').read()[0]
				return action
			else:
				raise exceptions.Warning("Vat Number should be in 9 or 12 Digits")
		else:
			raise exceptions.Warning("Vat Number should be in 9 or 12 Digits")

