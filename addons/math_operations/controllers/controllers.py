# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
from ..models.math_operations import MathOperations

class MathOperationApi(http.Controller):

    def _serialize_record(self,rec:MathOperations):
        return {
            'id': rec.id,
            'name': rec.name,
            'operand_1': rec.operand_1,
            'operand_2': rec.operand_2,
            'operation_type': rec.operation_type,
            'result': rec.result,
        }

    @http.route('/api/operations/get', type='json', auth='public', methods=['POST'], csrf=False)
    def get_operations(self, **kwargs):
        records = request.env['math.operations.clase'].sudo().search([])
        data = [self._serialize_record(rec) for rec in records]
        
        import json
        return request.make_response(
            json.dumps({'success': True, 'data': data, 'count': len(records)}),
            headers=[('Content-Type', 'application/json')]
        )

    

# class MathOperations(http.Controller):
#     @http.route('/math_operations/math_operations', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/math_operations/math_operations/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('math_operations.listing', {
#             'root': '/math_operations/math_operations',
#             'objects': http.request.env['math_operations.math_operations'].search([]),
#         })

#     @http.route('/math_operations/math_operations/objects/<model("math_operations.math_operations"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('math_operations.object', {
#             'object': obj
#         })
