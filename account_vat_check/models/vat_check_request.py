# -*- coding: utf-8 -*-
import requests
import json
import logging
import werkzeug
from odoo import models, exceptions
from datetime import datetime

_logger = logging.getLogger(__name__)


class MtdVATCheckAPi(models.Model):
	_name = 'mtd.vat_check_endpoint'
	_description = "check vat number api"

	def json_command(self, module_name=None, record_id=None,partner=None, timeout=5):
		try:
			header_items = {}
			record = self.env[module_name].search([('id', '=', record_id)])
			token = record.hmrc_configuration.get_access_token()
			if isinstance(token, list) and len(token) == 1:
				token = token[0]
			elif isinstance(token, str):
				pass
			else:
				raise exceptions.Warning('Invalid token format')
			header_items["authorization"] = ("Bearer " + token)

			hmrc_connection_url = "{}{}".format(record.hmrc_configuration.hmrc_url, record.path)

			_logger.info(
				"json_command - hmrc connection url:- {connection_url}, ".format(connection_url=hmrc_connection_url) +
				"headers:- {header}".format(header=header_items)
			)
			response = requests.get(hmrc_connection_url, timeout=timeout, headers=header_items)
			return self.handle_request_response(response, partner, hmrc_connection_url, record.company_type)
		except ValueError:

			return True

	def handle_request_response(self, response, record=None, url=None, company_type=None):
		response_token = json.loads(response.text)
		if response.status_code == 200:
			target = response_token.get('target')
			message = (
					"Date {date}     Time {time} \n".format(date=datetime.now().date(),
															time=datetime.now().time())
					+ "Congratulations ! The connection succeeded. \n"
					+ "Please check the log below for details. \n\n"
					+ "Connection Status Details: \n"
					+ "Request Sent: \n{connection_url} \n\n".format(connection_url=url)
					+ "Response Received: \n{message}".format(message=response_token or response_token['message'] or '')
			)
			partner_dict = {
				'name': target['name'],
				'street': target['address']['line1'],
				'zip': target['address']['postcode'],
				'response_from_hmrc': message
			}
			record.write(partner_dict)

		if 'message' in response_token:
			record.write({'response_from_hmrc': "Response Received From HMRC: \n" + response_token['message'].replace('targetVrn', 'VAT Number') })
		history_dict = {
			'partner_id': record.id,
			'vat': record.vat,
			'company_type': company_type,
			'processin_date': datetime.now(),
			'consultationNumber': response_token.get('consultationNumber') or '',
			'requester': response_token.get('requester') or '',
			'response_from_hmrc': response.text,
			'status_code': str(response.status_code),
		}
		self.env['vat.check.history'].create(history_dict)
		return True
