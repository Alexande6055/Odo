# -*- coding: utf-8 -*-
import logging
import requests
from dateutil import parser
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    gps_imei = fields.Char(
        string='IMEI del GPS',
        copy=False,
        index=True,
        help="Número IMEI o identificador único del hardware GPS en Traccar"
    )
    traccar_device_id = fields.Integer(
        string='ID Dispositivo Traccar',
        readonly=True,
        copy=False,
        help="Identificador del dispositivo asignado por el servidor Traccar"
    )
    traccar_status = fields.Char(
        string='Estado Traccar',
        readonly=True,
        copy=False,
        help="Estado reportado por Traccar (online, offline, unknown)"
    )
    last_latitude = fields.Float(
        string='Última Latitud',
        digits=(10, 7),
        readonly=True,
        copy=False
    )
    last_longitude = fields.Float(
        string='Última Longitud',
        digits=(10, 7),
        readonly=True,
        copy=False
    )
    last_speed = fields.Float(
        string='Velocidad (km/h)',
        digits=(6, 2),
        readonly=True,
        copy=False
    )
    last_gps_update = fields.Datetime(
        string='Última Actualización GPS',
        readonly=True,
        copy=False
    )
    google_maps_url = fields.Char(
        string='URL Google Maps',
        compute='_compute_google_maps_url'
    )

    @api.depends('last_latitude', 'last_longitude')
    def _compute_google_maps_url(self):
        for vehicle in self:
            if vehicle.last_latitude or vehicle.last_longitude:
                vehicle.google_maps_url = f"https://www.google.com/maps?q={vehicle.last_latitude},{vehicle.last_longitude}"
            else:
                vehicle.google_maps_url = False

    def _get_traccar_config(self):
        """Obtiene la configuración del servidor Traccar desde los parámetros del sistema."""
        ICP = self.env['ir.config_parameter'].sudo()
        url = (ICP.get_param('fleet_traccar.server_url') or 'http://traccar:8082').strip().rstrip('/')
        user = (ICP.get_param('fleet_traccar.user') or '').strip()
        password = ICP.get_param('fleet_traccar.password') or ''
        return url, user, password

    @api.model_create_multi
    def create(self, vals_list):
        vehicles = super(FleetVehicle, self).create(vals_list)
        for vehicle in vehicles:
            if vehicle.gps_imei and not vehicle.traccar_device_id:
                vehicle._create_device_in_traccar(raise_exception=False)
        return vehicles

    def write(self, vals):
        res = super(FleetVehicle, self).write(vals)
        if 'gps_imei' in vals:
            for vehicle in self:
                if vehicle.gps_imei and not vehicle.traccar_device_id:
                    vehicle._create_device_in_traccar(raise_exception=False)
        return res

    def action_register_traccar_device(self):
        """Acción de botón manual para registrar o vincular el vehículo con Traccar."""
        self.ensure_one()
        return self._create_device_in_traccar(raise_exception=True)

    def _create_device_in_traccar(self, raise_exception=False):
        """Registra el dispositivo en Traccar o lo vincula si ya existe."""
        self.ensure_one()
        if not self.gps_imei:
            if raise_exception:
                raise UserError(_("Debe definir el IMEI del GPS antes de vincular con Traccar."))
            return False

        url, user, password = self._get_traccar_config()
        if not user or not password:
            msg = _("Credenciales de Traccar no configuradas en Ajustes de Flota.")
            _logger.warning(msg)
            if raise_exception:
                raise UserError(msg)
            return False

        auth = (user, password)
        headers = {'Content-Type': 'application/json'}

        try:
            # 1. Comprobar si ya existe un dispositivo con este uniqueId en Traccar
            check_res = requests.get(
                f"{url}/api/devices",
                params={'uniqueId': self.gps_imei},
                auth=auth,
                headers=headers,
                timeout=5
            )
            if check_res.status_code == 200:
                devices = check_res.json()
                if devices and len(devices) > 0:
                    device = devices[0]
                    self.write({
                        'traccar_device_id': device.get('id'),
                        'traccar_status': device.get('status', 'desconocido')
                    })
                    if raise_exception:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _("Dispositivo Vinculado"),
                                'message': _("El dispositivo ya existía en Traccar y ha sido vinculado (ID: %s).") % device.get('id'),
                                'type': 'success',
                                'sticky': False,
                            }
                        }
                    return True

            # 2. Si no existe, crearlo
            payload = {
                "name": self.name or self.license_plate or self.gps_imei,
                "uniqueId": self.gps_imei
            }
            create_res = requests.post(
                f"{url}/api/devices",
                json=payload,
                auth=auth,
                headers=headers,
                timeout=5
            )

            if create_res.status_code in (200, 201):
                device_data = create_res.json()
                self.write({
                    'traccar_device_id': device_data.get('id'),
                    'traccar_status': device_data.get('status', 'desconocido')
                })
                if raise_exception:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _("¡Dispositivo Creado!"),
                            'message': _("Dispositivo creado con éxito en Traccar (ID: %s).") % device_data.get('id'),
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                return True
            else:
                msg = _("Error de Traccar (HTTP %s): %s") % (create_res.status_code, create_res.text)
                _logger.warning("No se pudo crear el dispositivo en Traccar: %s", msg)
                if raise_exception:
                    raise UserError(msg)
                return False

        except requests.exceptions.RequestException as e:
            msg = _("Error de conexión con Traccar: %s") % str(e)
            _logger.error(msg)
            if raise_exception:
                raise UserError(msg)
            return False

    def action_sync_traccar_positions(self):
        """Consulta y actualiza la última posición del vehículo desde Traccar."""
        url, user, password = self._get_traccar_config()
        if not user or not password:
            raise UserError(_("Configure el usuario y contraseña de Traccar en los Ajustes de Flota."))

        auth = (user, password)
        headers = {'Accept': 'application/json'}

        updated_count = 0
        last_info = ""

        for vehicle in self:
            if not vehicle.traccar_device_id:
                # Intentar vincular si tiene IMEI
                if vehicle.gps_imei:
                    vehicle._create_device_in_traccar(raise_exception=False)
                if not vehicle.traccar_device_id:
                    continue

            try:
                # Consultar estado del dispositivo
                dev_res = requests.get(
                    f"{url}/api/devices",
                    params={'id': vehicle.traccar_device_id},
                    auth=auth,
                    headers=headers,
                    timeout=5
                )
                if dev_res.status_code == 200:
                    dev_data = dev_res.json()
                    if dev_data:
                        vehicle.traccar_status = dev_data[0].get('status', 'desconocido')

                # Consultar última posición
                pos_res = requests.get(
                    f"{url}/api/positions",
                    params={'deviceId': vehicle.traccar_device_id},
                    auth=auth,
                    headers=headers,
                    timeout=5
                )
                if pos_res.status_code == 200:
                    positions = pos_res.json()
                    if positions and isinstance(positions, list):
                        # La última posición suele ser la última de la lista o la de mayor fixTime
                        latest = sorted(positions, key=lambda p: p.get('fixTime') or '', reverse=True)[0]
                        lat = latest.get('latitude', 0.0)
                        lon = latest.get('longitude', 0.0)
                        speed_knots = latest.get('speed', 0.0)
                        speed_kmh = round(float(speed_knots) * 1.852, 2)

                        fix_time_str = latest.get('fixTime') or latest.get('deviceTime')
                        fix_datetime = False
                        if fix_time_str:
                            try:
                                dt = parser.parse(fix_time_str)
                                fix_datetime = dt.strftime('%Y-%m-%d %H:%M:%S')
                            except Exception:
                                fix_datetime = fields.Datetime.now()

                        vals = {
                            'last_latitude': lat,
                            'last_longitude': lon,
                            'last_speed': speed_kmh,
                        }
                        if fix_datetime:
                            vals['last_gps_update'] = fix_datetime

                        vehicle.write(vals)
                        updated_count += 1
                        last_info = f"Lat: {lat}, Lon: {lon}, Vel: {speed_kmh} km/h"
                    else:
                        _logger.info("El dispositivo ID %s no tiene posiciones reportadas todavía en Traccar.", vehicle.traccar_device_id)
            except requests.exceptions.RequestException as e:
                _logger.error("Error al sincronizar posición de Traccar para vehículo %s: %s", vehicle.name, str(e))

        if len(self) == 1:
            if updated_count > 0:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Posición Sincronizada"),
                        'message': _("Última ubicación obtenida: %s") % last_info,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Sin Posiciones"),
                        'message': _("El dispositivo no tiene posiciones GPS registradas aún en Traccar."),
                        'type': 'warning',
                        'sticky': False,
                    }
                }
        return True

    def action_open_google_maps(self):
        """Abre la ubicación actual del vehículo en Google Maps."""
        self.ensure_one()
        if not self.last_latitude and not self.last_longitude:
            raise UserError(_("Este vehículo aún no cuenta con coordenadas GPS sincronizadas."))
        return {
            'type': 'ir.actions.act_url',
            'url': f"https://www.google.com/maps?q={self.last_latitude},{self.last_longitude}",
            'target': 'new'
        }

    @api.model
    def cron_sync_all_traccar_positions(self):
        """Método ejecutado periódicamente por el cron para actualizar coordenadas de todos los vehículos vinculados."""
        vehicles = self.search([('traccar_device_id', '>', 0)])
        if vehicles:
            _logger.info("Iniciando sincronización programada de Traccar para %d vehículos...", len(vehicles))
            vehicles.action_sync_traccar_positions()