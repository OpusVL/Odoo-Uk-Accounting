from openerp import models, fields, api, exceptions
from datetime import datetime, timedelta

class VatNumberHistory(models.Model):
	_name = 'vat.check.history'
	_description = 'Checked Vat Number History'
	_order = 'create_date desc'

	partner_id = fields.Many2one('res.partner',string='Contact')
	vat = fields.Char('Vat Number')
	company_type = fields.Selection(
		string='Endpoint Type',
		selection=[('company', 'Company'), ('business', 'Business')],
	)
	processin_date = fields.Datetime(string='Processed On')
	consultationNumber = fields.Char(string='Consultation Number')
	requester = fields.Char(string='Requester')
	response_from_hmrc = fields.Text(string="Response From HMRC", readonly=True)
	status = fields.Char('Status')
	status_code = fields.Char('Status')
