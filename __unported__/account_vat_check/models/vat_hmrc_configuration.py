# -*- coding: utf-8 -*-
import requests
import logging
from odoo import models, fields, exceptions

_logger = logging.getLogger(__name__)


class MtdVATHmrcConfiguration(models.Model):
    _name = 'mtd.vat_hmrc_configuration'
    _description = "user parameters to connect to HMRC's MTD API's"

    name = fields.Char(required=True)
    environment = fields.Selection([
        ('sandbox', ' Sandbox'),
        ('live', ' Live'),
    ],  string="HMRC Environment",
        required=True)
    hmrc_url = fields.Char('HMRC URL', required=True)

