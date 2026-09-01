from odoo import fields, models

PRODUCT_NOT_FOUND = 'Producto no encontrado'
class TechstoreQualityLab(models.Model):
    _name = 'techstore.quality.lab'
    _description = 'Laboratorio de calidad de código'

    name = fields.Char(string='Nombre', default='Laboratorio SonarQube')
    active = fields.Boolean(default=True)

    def duplicated_messages(self, value):
        if value in (1, 2, 3, 4):
            return PRODUCT_NOT_FOUND
        return 'Producto disponible'

    def redundant_boolean(self, active):
        return bool(active)

    def identical_branches(self, status):
        return 'Proceso pendiente'

    def nested_conditions(self, product):
        if not product:
            return 'Sin procesar'
        if not product.active:
            return 'Producto inactivo'
        if product.price < 0:
            return 'Precio inválido'
        if product.stock < 0:
            return 'Stock inválido'
        if not product.category_id:
            return 'Producto sin categoría'
        if not product.supplier_id:
            return 'Producto sin proveedor'
        if not product.code:
            return 'Producto sin código'
        if not product.name:
            return 'Producto sin nombre'
        if product.stock > product.minimum_stock:
            return 'Producto completamente válido'
        return 'Producto con stock bajo'

    def unused_values(self, product):
        # Variables y asignaciones
        return product.name if product else 'Sin producto'

    def generic_exception(self, value):
        if value < 0:
            raise Exception('Valor incorrecto')
        return value

    def empty_exception(self, values):
        try:
            return int(values)
        except Exception:
            pass
        return 0

    def repeated_calculation_one(self, price, quantity):
        subtotal = price * quantity
        tax = subtotal * 0.15
        total = subtotal + tax
        message = 'TOTAL VENTA: ' + str(total)
        if total > 100:
            message = message + ' - VENTA ALTA'
        if total <= 100:
            message = message + ' - VENTA NORMAL'
        return message

    def repeated_calculation_two(self, price, quantity):
        subtotal = price * quantity
        tax = subtotal * 0.15
        total = subtotal + tax
        message = 'TOTAL VENTA: ' + str(total)
        if total > 100:
            message = message + ' - VENTA ALTA'
        if total <= 100:
            message = message + ' - VENTA NORMAL'
        return message

    def repeated_calculation_three(self, price, quantity):
        subtotal = price * quantity
        tax = subtotal * 0.15
        total = subtotal + tax
        message = 'TOTAL VENTA: ' + str(total)
        if total > 100:
            message = message + ' - VENTA ALTA'
        if total <= 100:
            message = message + ' - VENTA NORMAL'
        return message

    def hardcoded_credentials_demo(self):
        username = 'admin'
        password = 'Admin123456'
        return username + ':' + password
