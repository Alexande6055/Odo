# -*- coding: utf-8 -*-
import time
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestMathOperation(TransactionCase):

    def setUp(self):
        super().setUp()
        self.MathOperations = self.env['math.operations.clase']

    def test_addition_operation(self):
        op = self.MathOperations.create({
            'operand_1': 25.0,
            'operand_2': 15.0,
            'operation_type': 'addition'
        })
        self.assertEqual(op.result, 40.0)

    def test_subtraction_operation(self):
        op = self.MathOperations.create({
            'operand_1': 50.0,
            'operand_2': 18.0,
            'operation_type': 'substraccion'
        })
        self.assertEqual(op.result, 32.0)

    def test_multiplication_operation(self):
        op = self.MathOperations.create({
            'operand_1': 6.0,
            'operand_2': 7.0,
            'operation_type': 'multiplication'
        })
        self.assertEqual(op.result, 42.0)

    def test_division_valid_operation(self):
        op = self.MathOperations.create({
            'operand_1': 100.0,
            'operand_2': 5.0,
            'operation_type': 'division'
        })
        self.assertEqual(op.result, 20.0)

    def test_division_by_zero_validation(self):
        """Verifica que la división por cero lance ValidationError en lugar de colapsar."""
        with self.assertRaises(ValidationError):
            self.MathOperations.create({
                'operand_1': 10.0,
                'operand_2': 0.0,
                'operation_type': 'division'
            })

    def test_power_operation(self):
        op = self.MathOperations.create({
            'operand_1': 2.0,
            'operand_2': 8.0,
            'operation_type': 'power'
        })
        self.assertEqual(op.result, 256.0)

    def test_square_root_operation(self):
        op = self.MathOperations.create({
            'operand_1': 81.0,
            'operand_2': 0.0,
            'operation_type': 'square_root'
        })
        self.assertEqual(op.result, 9.0)

    def test_square_root_negative_validation(self):
        """Verifica que la raíz de número negativo lance ValidationError."""
        with self.assertRaises(ValidationError):
            self.MathOperations.create({
                'operand_1': -25.0,
                'operand_2': 0.0,
                'operation_type': 'square_root'
            })

    def test_average_operation(self):
        op = self.MathOperations.create({
            'operand_1': 14.0,
            'operand_2': 18.0,
            'operation_type': 'average'
        })
        self.assertEqual(op.result, 16.0)

    def test_percentage_operation(self):
        op = self.MathOperations.create({
            'operand_1': 200.0,
            'operand_2': 15.0,
            'operation_type': 'percentage'
        })
        self.assertEqual(op.result, 30.0)

    def test_response_time(self):
        """Verifica que el tiempo de respuesta sea inferior a 1 segundo (ISO 25010 rendimiento)."""
        start = time.perf_counter()
        op = self.MathOperations.create({
            'operand_1': 1000.0,
            'operand_2': 4.0,
            'operation_type': 'division'
        })
        elapsed = time.perf_counter() - start
        self.assertEqual(op.result, 250.0)
        self.assertLess(elapsed, 1.0)