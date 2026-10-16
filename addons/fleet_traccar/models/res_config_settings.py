# -*- coding: utf-8 -*-
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    traccar_server_url = fields.Char(
        string='URL de Traccar',
        config_parameter='fleet_traccar.server_url',
        default='http://traccar:8082',
        help="URL interna del contenedor Traccar (ej. http://traccar:8082)"
    )
    traccar_user = fields.Char(
        string='Usuario / Email de Traccar',
        config_parameter='fleet_traccar.user',
        help="Correo electrónico o usuario registrado en Traccar"
    )
    traccar_password = fields.Char(
        string='Contraseña de Traccar',
        config_parameter='fleet_traccar.password',
        help="Contraseña del usuario o token de Traccar"
    )

    def action_test_traccar_connection(self):
        """Prueba la conectividad y las credenciales con el servidor Traccar."""
        self.ensure_one()
        url = (self.traccar_server_url or '').strip().rstrip('/')
        user = (self.traccar_user or '').strip()
        password = self.traccar_password or ''

        if not url:
            raise UserError(_("Debe ingresar la URL del servidor Traccar."))

        # 1. Probar conectividad al servidor
        try:
            server_res = requests.get(f"{url}/api/server", timeout=5)
            if server_res.status_code != 200:
                raise UserError(_("El servidor respondió con código HTTP %s al consultar el estado.") % server_res.status_code)
            server_info = server_res.json()
            version = server_info.get('version', 'desconocida')
        except requests.exceptions.RequestException as e:
            raise UserError(_("No se pudo conectar al contenedor Traccar en '%s'. Verifique que la red Docker esté configurada y el contenedor esté activo.\nDetalle: %s") % (url, str(e)))

        # 2. Si se proporcionó usuario y contraseña, probar autenticación
        if user and password:
            try:
                auth_res = requests.post(
                    f"{url}/api/session",
                    data={'email': user, 'password': password},
                    timeout=5
                )
                if auth_res.status_code == 200:
                    user_data = auth_res.json()
                    user_name = user_data.get('name') or user
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _("¡Conexión Exitosa!"),
                            'message': _("Conectado correctamente con Traccar v%s como '%s'.") % (version, user_name),
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                elif auth_res.status_code == 401:
                    raise UserError(_("Conexión con el servidor OK, pero las credenciales (usuario/contraseña) fueron rechazadas por Traccar (401 Unauthorized)."))
                else:
                    raise UserError(_("Error de autenticación con Traccar (HTTP %s): %s") % (auth_res.status_code, auth_res.text))
            except requests.exceptions.RequestException as e:
                raise UserError(_("Error al validar credenciales con Traccar: %s") % str(e))
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Servidor Alcanzable"),
                    'message': _("Traccar v%s está en línea, pero ingrese usuario y contraseña para validar el acceso.") % version,
                    'type': 'warning',
                    'sticky': False,
                }
            }
