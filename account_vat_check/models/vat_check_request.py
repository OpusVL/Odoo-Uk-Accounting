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
		response_token_message = ''
		partner_dict = {}
		if response.status_code == 200:
			target = response_token.get('target')
			for field in target.keys():
				if field != 'address':
					response_token_message += "{field} : {value} \n".format(field=field,value=target[field])
			if 'address' in target.keys():
				response_token_message += "\nAddress\n"
				for field in target['address']:
					response_token_message += "{field} : {value} \n".format(field=field,value=target['address'][field])

			message = (
					"Date {date}     Time {time} \n".format(date=datetime.now().date(),
															time=datetime.now().time())
					+ "Congratulations ! The connection succeeded. \n"
					+ "Please check the log below for details. \n\n"
					+ "Response Received: \n{message}".format(message=response_token_message or '')
			)
			partner_dict = {
				'name': target['name'],
				'street': target['address']['line1'],
				'zip': target['address']['postcode'],
				'response_from_hmrc': message
			}
		if 'message' in response_token:
			if company_type == 'company':
				response_token_message = response_token['message'].replace('targetVrn', 'VAT Number')
			else:
				response_token_message = response_token['message'].replace('requesterVrn', 'Company (Requester) VAT Number')
			partner_dict.update({'response_from_hmrc': "Response Received From HMRC: \n {}".format(response_token_message) })
		
		record.write(partner_dict)
		history_dict = {
			'partner_id': record.id,
			'vat': record.vat,
			'company_type': company_type,
			'processin_date': datetime.now(),
			'consultationNumber': response_token.get('consultationNumber') or '',
			'requester': response_token.get('requester') or '',
			'response_from_hmrc':response_token_message or '',
			'status': 'Success' if response.status_code == 200 else 'Failed',
			'status_code': "{}".format(response.status_code),
		}
		self.env['vat.check.history'].create(history_dict)
		return True
