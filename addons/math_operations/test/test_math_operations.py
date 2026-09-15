
from odoo.tests.common import TransactionCase


class TestMathOperation(TransactionCase):
    def setUp(self):
        super().setUp()
        self.MathOperations = self.env['math.operations.clase']

    def test_sum_operation(self):
        op = self.MathOperations.create({
            'operand_1': 2,
            'operand_2': 5,
            'operation_type': 'addition'
        })
        self.assertEqual(op.result, 7)

    def test_multiplication_operation(self):
        op = self.MathOperations.create({
            'operand_1': 4,
            'operand_2': 3,
            'operation_type': 'multiplication'
        })
        self.assertEqual(op.result, 12)

    def test_division_operation(self):
        op = self.MathOperations.create({
            'operand_1': 20,
            'operand_2': 4,
            'operation_type': 'division'
        })
        self.assertEqual(op.result, 5)

    def test_power_operation(self):
        op = self.MathOperations.create({
            'operand_1': 2,
            'operand_2': 3,
            'operation_type': 'power'
        })
        self.assertEqual(op.result, 8)