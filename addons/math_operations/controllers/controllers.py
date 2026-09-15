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

    @http.route('/api/operations/get', type='http', auth='public', methods=['GET'], csrf=False)
    def get_operations(self, **kwargs):
        records = request.env['math.operations.clase'].sudo().search([])
        data = [self._serialize_record(rec) for rec in records]
        
        import json
        return request.make_response(
            json.dumps({'success': True, 'data': data, 'count': len(records)}),
            headers=[('Content-Type', 'application/json')]
        )

    # CONSULTAR POR ID
    @http.route('/api/operations/get/<int:record_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_operation_by_id(self, record_id, **kwargs):
        rec = request.env['math.operations.clase'].sudo().browse(record_id)
        import json
        if not rec.exists():
            return request.make_response(
                json.dumps({
                    'success': False,
                    'message': 'Registro no encontrado'
                }),
                headers=[('Content-Type', 'application/json')]
            )
        return request.make_response(
            json.dumps({
                'success': True,
                'data': self._serialize_record(rec)
            }),
            headers=[('Content-Type', 'application/json')]
        )

    # CREAR
    @http.route('/api/operations/create', type='json', auth='public', methods=['POST'], csrf=False)
    def create_operation(self, operand_1, operand_2, operation_type, notes=None):
        try:
            vals = {
                'operand_1': operand_1,
                'operand_2': operand_2,
                'operation_type': operation_type,
                'notes': notes,
            }
            rec = request.env['math.operations.clase'].sudo().create(vals)
            return {
                'success': True,
                'message': 'Operación creada correctamente',
                'data': self._serialize_record(rec)
            }
        except ValidationError as e:
            return {
                'success': False,
                'message': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error interno: {str(e)}'
            }

    # ACTUALIZAR
    @http.route('/api/operations/update', type='json', auth='public', methods=['POST'], csrf=False) 
    def update_operation(self, record_id, **kwargs):
        rec = request.env['math.operations.clase'].sudo().browse(record_id)
        if not rec.exists():
            return {
                'success': False,
                'message': 'Registro no encontrado'
            }
        try:
            vals = {}
            if 'operand_1' in kwargs:
                vals['operand_1'] = kwargs.get('operand_1')
            if 'operand_2' in kwargs:
                vals['operand_2'] = kwargs.get('operand_2')
            if 'operation_type' in kwargs:
                vals['operation_type'] = kwargs.get('operation_type')
            if 'notes' in kwargs:
                vals['notes'] = kwargs.get('notes')
            rec.write(vals)
            return {
                'success': True,
                'message': 'Operación actualizada correctamente',
                'data': self._serialize_record(rec)
            }
        except ValidationError as e:
            return {
                'success': False,
                'message': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error interno: {str(e)}'
            }
    # ELIMINAR
    @http.route('/api/operations/delete', type='json', auth='public', methods=['POST'], csrf=False)
    def delete_operation(self, record_id):
        rec = request.env['math.operations.clase'].sudo().browse(record_id)
        if not rec.exists():
            return {
            'success': False,
            'message': 'Registro no encontrado'
            }
        rec.unlink()
        return {
            'success': True,
            'message': 'Operación eliminada correctamente'
            }
    