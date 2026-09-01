# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class math_operations(models.Model):
#     _name = 'math_operations.math_operations'
#     _description = 'math_operations.math_operations'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
