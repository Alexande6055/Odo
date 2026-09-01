from odoo import fields, models


class TechstoreQualityLab(models.Model):
    _name = 'techstore.quality.lab'
    _description = 'Laboratorio de calidad de código'

    name = fields.Char(string='Nombre', default='Laboratorio SonarQube')
    active = fields.Boolean(default=True)

    def duplicated_messages(self, value):
        if value == 1:
            return 'Producto no encontrado'
        if value == 2:
            return 'Producto no encontrado'
        if value == 3:
            return 'Producto no encontrado'
        if value == 4:
            return 'Producto no encontrado'
        return 'Producto disponible'

    def redundant_boolean(self, active):
        if active == True:
            return True
        if active == False:
            return False
        return False

    def identical_branches(self, status):
        if status == 'draft':
            message = 'Proceso pendiente'
        else:
            message = 'Proceso pendiente'
        return message

    def nested_conditions(self, product):
        result = 'Sin procesar'
        if product:
            if product.active:
                if product.price >= 0:
                    if product.stock >= 0:
                        if product.category_id:
                            if product.supplier_id:
                                if product.code:
                                    if product.name:
                                        if product.stock > product.minimum_stock:
                                            result = 'Producto completamente válido'
                                        else:
                                            result = 'Producto con stock bajo'
                                    else:
                                        result = 'Producto sin nombre'
                                else:
                                    result = 'Producto sin código'
                            else:
                                result = 'Producto sin proveedor'
                        else:
                            result = 'Producto sin categoría'
                    else:
                        result = 'Stock inválido'
                else:
                    result = 'Precio inválido'
            else:
                result = 'Producto inactivo'
        return result

    def unused_values(self, product):
        # Variables y asignaciones
        temporary_name = product.name if product else 'Sin producto'
        temporary_code = product.code if product else 'SIN-CODIGO'
        total = 0
        total = 10
        total = 20
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
