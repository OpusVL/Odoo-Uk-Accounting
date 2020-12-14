from odoo import models, fields, api, exceptions
from datetime import datetime, timedelta

class ResPartner(models.Model):
	_inherit = 'res.partner'

	response_from_hmrc = fields.Text(string="Response From HMRC", readonly=True)