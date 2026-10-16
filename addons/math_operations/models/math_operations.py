# -*- coding: utf-8 -*-
import math
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class MathOperations(models.Model):
    _name = 'math.operations.clase'
    _description = 'Math Operations'
    _order = 'id desc'
    
    name = fields.Char(
        string='Description',
        compute='_compute_name',
        store=True
    )

    operand_1 = fields.Float(string='Operand 1', required=True)
    operand_2 = fields.Float(string='Operand 2', required=True, default=0.0)

    operation_type = fields.Selection([
        ('addition', 'Adición / Suma'),
        ('substraccion', 'Sustracción / Resta'),
        ('multiplication', 'Multiplicación'),
        ('division', 'División'),
        ('power', 'Potencia (Power)'),
        ('square_root', 'Raíz Cuadrada (Sqrt)'),
        ('average', 'Promedio (Avg)'),
        ('percentage', 'Porcentaje (Percent)'),
        # Aliases para compatibilidad con pruebas unitarias, slides y API REST
        ('suma', 'Suma'),
        ('resta', 'Resta'),
        ('multiplicacion', 'Multiplicación'),
        ('div', 'División'),
        ('potencia', 'Potencia'),
        ('pow', 'Power'),
        ('raiz_cuadrada', 'Raíz Cuadrada'),
        ('sqrt', 'Sqrt'),
        ('promedio', 'Promedio'),
        ('avg', 'Avg'),
        ('porcentaje', 'Porcentaje'),
        ('percent', 'Percent'),
    ],
    string='Operation Type',
    required=True,
    default='addition'
    )

    result = fields.Float(string='Result', compute='_compute_result', store=True, digits=(16, 6))
    operation_date = fields.Datetime(string='Operation Date', default=fields.Datetime.now, required=True)
    user_id = fields.Many2one(
        'res.users', string='User', default=lambda self: self.env.user
    )

    notes = fields.Text(string='Notes')

    @api.depends('operand_1', 'operand_2', 'operation_type')
    def _compute_name(self):
        for rec in self:
            if rec.operation_type:
                op_name = dict(rec._fields['operation_type'].selection).get(rec.operation_type, rec.operation_type)
                if rec.operation_type in ('square_root', 'sqrt', 'raiz_cuadrada'):
                    rec.name = f"{op_name.upper()} ({rec.operand_1})"
                else:
                    rec.name = f"{op_name.upper()} ({rec.operand_1}, {rec.operand_2})"

    @api.depends('operand_1', 'operand_2', 'operation_type')
    def _compute_result(self):
        for rec in self:
            op = rec.operation_type
            if op in ('addition', 'suma'):
                rec.result = rec.operand_1 + rec.operand_2
            elif op in ('substraccion', 'resta'):
                rec.result = rec.operand_1 - rec.operand_2
            elif op in ('multiplication', 'multiplicacion'):
                rec.result = rec.operand_1 * rec.operand_2
            elif op in ('division', 'div'):
                if rec.operand_2 == 0:
                    raise ValidationError('No se permite la división por cero.')
                rec.result = rec.operand_1 / rec.operand_2
            elif op in ('power', 'potencia', 'pow'):
                if rec.operand_1 == 0 and rec.operand_2 < 0:
                    raise ValidationError('No se puede elevar cero a una potencia negativa.')
                try:
                    rec.result = rec.operand_1 ** rec.operand_2
                except OverflowError:
                    raise ValidationError('El resultado de la potencia excede el límite numérico permitido (Overflow).')
            elif op in ('square_root', 'sqrt', 'raiz_cuadrada'):
                if rec.operand_1 < 0:
                    raise ValidationError('No se puede calcular la raíz cuadrada de un número negativo.')
                rec.result = math.sqrt(rec.operand_1)
            elif op in ('average', 'avg', 'promedio'):
                rec.result = (rec.operand_1 + rec.operand_2) / 2.0
            elif op in ('percentage', 'percent', 'porcentaje'):
                rec.result = (rec.operand_1 * rec.operand_2) / 100.0
            else:
                rec.result = 0.0

    @api.constrains('operation_type', 'operand_1', 'operand_2')
    def _check_operation_constraints(self):
        for rec in self:
            op = rec.operation_type
            if op in ('division', 'div') and rec.operand_2 == 0:
                raise ValidationError('Validación de Calidad: No se permite la división por cero.')
            if op in ('square_root', 'sqrt', 'raiz_cuadrada') and rec.operand_1 < 0:
                raise ValidationError('Validación de Calidad: No se puede calcular la raíz cuadrada de un número negativo.')
            if op in ('power', 'potencia', 'pow') and rec.operand_1 == 0 and rec.operand_2 < 0:
                raise ValidationError('Validación de Calidad: No se puede elevar cero a una potencia negativa.')