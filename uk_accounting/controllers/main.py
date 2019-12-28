# -*- coding: utf-8 -*-

import logging
from odoo import http, exceptions


_logger = logging.getLogger(__name__)


class Authorize(http.Controller):
    
    @http.route('/auth-redirect', type='http', methods=['GET'])
    def get_epdq_response(self, **args):
        return True
