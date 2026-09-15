from odoo import models,fields,api
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

    operand_1 = fields.Float(string='Operand 1',required=True)
    operand_2 = fields.Float(string='Operand 2',required=True)

    
    operation_type = fields.Selection([
        ('addition','Adition'),
        ('substraccion','Substraccion'),
        ('multiplication','Multiplication'),
        ('division','Division'),
        ('power','Power'),
        ],
        string='operation type',
        required=True,
        default='addition'
        )

    result = fields.Float(string='Result',compute='_compute_result',store=True)
    operation_date = fields.Datetime(string='Operation Date', default=fields.Datetime.now, required=True)
    user_id=  fields.Many2one(
        'res.users',string='User',default = lambda self:self.env.user
    )

    notes= fields.Text(string='Notes')

    @api.depends('operand_1','operand_2','operation_type')
    def _compute_name(self):
        for rec in self:
            if rec.operation_type:
                rec.name=f"{rec.operation_type.upper()} ({rec.operand_1},{rec.operand_2})"

    @api.depends('operand_1','operand_2','operation_type')
    def _compute_result(self):
        for rec in self:
            if rec.operation_type=='addition':
                rec.result=rec.operand_1+rec.operand_2
            elif rec.operation_type=='substraccion':
                rec.result=rec.operand_1-rec.operand_2
            elif rec.operation_type=='multiplication':
                rec.result=rec.operand_1*rec.operand_2
            elif rec.operation_type=='division':
                rec.result=rec.operand_1/rec.operand_2
            elif rec.operation_type=='power':
                rec.result=rec.operand_1**rec.operand_2
    
    @api.constrains('operation_type', 'operand_2')
    def _constrain_division_by_zero(self):
        for rec in self:
            if rec.operation_type=='division' and rec.operand_2==0:
                raise ValidationError('Division by zero is not allowed')