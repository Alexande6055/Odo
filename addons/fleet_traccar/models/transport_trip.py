# -*- coding: utf-8 -*-
import json
import logging
from datetime import timedelta
from dateutil import parser
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .geo_utils import haversine_distance, min_distance_to_path, calculate_total_path_distance

_logger = logging.getLogger(__name__)

class TransportTrip(models.Model):
    _name = 'transport.trip'
    _description = 'Recorrido / Viaje Programado'
    _order = 'date desc, scheduled_start_time desc, id desc'

    name = fields.Char(
        string='Código de Recorrido',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo')
    )
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo / Bus',
        required=True,
        index=True
    )
    driver_id = fields.Many2one(
        'res.partner',
        string='Conductor Asignado'
    )
    route_id = fields.Many2one(
        'transport.route',
        string='Ruta Asignada',
        required=True,
        index=True
    )
    date = fields.Date(
        string='Fecha del Recorrido',
        required=True,
        default=fields.Date.context_today,
        index=True
    )
    scheduled_start_time = fields.Datetime(
        string='Salida Programada',
        required=True,
        index=True
    )
    scheduled_end_time = fields.Datetime(
        string='Llegada Programada',
        required=True
    )
    actual_start_time = fields.Datetime(
        string='Salida Real Registrada'
    )
    actual_end_time = fields.Datetime(
        string='Llegada Real Registrada'
    )
    state = fields.Selection([
        ('draft', 'Borrador / Programado'),
        ('in_progress', 'En Curso'),
        ('completed', 'Completado / Finalizado'),
        ('cancelled', 'Cancelado')
    ], string='Estado del Viaje', default='draft', required=True, index=True)

    compliance_status = fields.Selection([
        ('pending', 'Pendiente de Evaluación'),
        ('compliant', 'Cumplido / Puntual'),
        ('delayed', 'Cumplido con Retraso'),
        ('non_compliant', 'Incumplido / No Conforme')
    ], string='Evaluación de Cumplimiento', default='pending', store=True, compute='_compute_compliance_status')

    estimated_distance = fields.Float(
        string='Distancia Estimada (km)',
        related='route_id.estimated_distance',
        store=True,
        digits=(6, 2)
    )
    actual_distance = fields.Float(
        string='Distancia Real (km)',
        digits=(8, 2),
        default=0.0,
        help="Distancia total acumulada a partir de los puntos GPS registrados."
    )
    distance_diff = fields.Float(
        string='Diferencia Distancia (km)',
        compute='_compute_metrics',
        store=True,
        digits=(8, 2),
        help="Diferencia: Distancia Real - Distancia Estimada"
    )
    duration_real_minutes = fields.Float(
        string='Duración Real (min)',
        compute='_compute_metrics',
        store=True,
        digits=(6, 1)
    )
    delay_minutes = fields.Float(
        string='Retraso Total (min)',
        compute='_compute_metrics',
        store=True,
        digits=(6, 1)
    )
    stop_completion_rate = fields.Float(
        string='% Paradas Cumplidas',
        compute='_compute_metrics',
        store=True,
        digits=(5, 2)
    )
    has_deviations = fields.Boolean(
        string='¿Tuvo Desviaciones?',
        compute='_compute_metrics',
        store=True
    )

    point_ids = fields.One2many(
        'transport.trip.point',
        'trip_id',
        string='Historial de Puntos GPS'
    )
    point_count = fields.Integer(
        string='N.º Puntos GPS',
        compute='_compute_counts'
    )
    stop_check_ids = fields.One2many(
        'transport.trip.stop.check',
        'trip_id',
        string='Control de Puntos de Parada'
    )
    stop_check_count = fields.Integer(
        string='N.º Paradas Controladas',
        compute='_compute_counts'
    )
    incident_ids = fields.One2many(
        'transport.trip.incident',
        'trip_id',
        string='Incidencias Registradas'
    )
    incident_count = fields.Integer(
        string='N.º Incidencias',
        compute='_compute_counts'
    )
    notes = fields.Text(string='Observaciones')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transport.trip') or _('Nuevo')
        records = super(TransportTrip, self).create(vals_list)
        for record in records:
            record._initialize_stop_checks()
        return records

    @api.depends('point_ids', 'stop_check_ids', 'incident_ids')
    def _compute_counts(self):
        for trip in self:
            trip.point_count = len(trip.point_ids)
            trip.stop_check_count = len(trip.stop_check_ids)
            trip.incident_count = len(trip.incident_ids)

    def _initialize_stop_checks(self):
        """Inicializa los controles de parada según la ruta asociada."""
        self.ensure_one()
        if self.route_id and not self.stop_check_ids:
            checks = []
            for stop in self.route_id.stop_ids:
                sched_time = False
                if self.scheduled_start_time:
                    sched_time = self.scheduled_start_time + timedelta(minutes=stop.expected_offset_minutes)
                checks.append((0, 0, {
                    'stop_id': stop.id,
                    'scheduled_time': sched_time,
                    'status': 'pending',
                }))
            if checks:
                self.write({'stop_check_ids': checks})

    @api.onchange('route_id', 'scheduled_start_time')
    def _onchange_route_schedule(self):
        if self.route_id and self.scheduled_start_time:
            self.scheduled_end_time = self.scheduled_start_time + timedelta(minutes=self.route_id.estimated_duration or 30)

    @api.depends('actual_start_time', 'actual_end_time', 'scheduled_end_time',
                 'actual_distance', 'estimated_distance', 'stop_check_ids.status',
                 'incident_ids.incident_type')
    def _compute_metrics(self):
        for trip in self:
            # 1. Duración real
            if trip.actual_start_time and trip.actual_end_time:
                delta = trip.actual_end_time - trip.actual_start_time
                trip.duration_real_minutes = round(delta.total_seconds() / 60.0, 1)
            else:
                trip.duration_real_minutes = 0.0

            # 2. Diferencia de distancia
            trip.distance_diff = round(trip.actual_distance - trip.estimated_distance, 2)

            # 3. Retraso total
            if trip.actual_end_time and trip.scheduled_end_time:
                delay_sec = (trip.actual_end_time - trip.scheduled_end_time).total_seconds()
                trip.delay_minutes = max(0.0, round(delay_sec / 60.0, 1))
            else:
                trip.delay_minutes = 0.0

            # 4. Porcentaje de paradas cumplidas
            total_stops = len(trip.stop_check_ids)
            if total_stops > 0:
                visited_stops = len(trip.stop_check_ids.filtered(lambda s: s.status in ('visited', 'delayed')))
                trip.stop_completion_rate = round((visited_stops / total_stops) * 100.0, 2)
            else:
                trip.stop_completion_rate = 100.0

            # 5. ¿Tuvo desviaciones?
            trip.has_deviations = bool(trip.incident_ids.filtered(lambda i: i.incident_type == 'route_deviation'))

    @api.depends('state', 'stop_completion_rate', 'has_deviations', 'delay_minutes', 'incident_ids')
    def _compute_compliance_status(self):
        for trip in self:
            if trip.state != 'completed':
                trip.compliance_status = 'pending'
                continue

            # Si faltaron paradas obligatorias o hubo desviaciones severas -> Incumplido
            has_missed = bool(trip.stop_check_ids.filtered(lambda s: s.status == 'missed'))
            if trip.has_deviations or has_missed or trip.stop_completion_rate < 80.0:
                trip.compliance_status = 'non_compliant'
            elif trip.delay_minutes > 5.0 or bool(trip.incident_ids.filtered(lambda i: i.incident_type == 'delay')):
                trip.compliance_status = 'delayed'
            else:
                trip.compliance_status = 'compliant'

    def action_start_trip(self):
        """Inicia el recorrido formalmente."""
        self.ensure_one()
        vals = {'state': 'in_progress'}
        if not self.actual_start_time:
            vals['actual_start_time'] = fields.Datetime.now()
        if not self.stop_check_ids:
            self._initialize_stop_checks()
        self.write(vals)

    def action_complete_trip(self):
        """Finaliza el recorrido y dispara el análisis automático."""
        self.ensure_one()
        vals = {'state': 'completed'}
        if not self.actual_end_time:
            vals['actual_end_time'] = fields.Datetime.now()
        self.write(vals)
        # Ejecutar análisis automático de cumplimiento de paradas, desvíos y retrasos
        self.action_analyze_trip()

    def action_cancel_trip(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.ensure_one()
        self.write({'state': 'draft', 'compliance_status': 'pending'})

    def action_sync_points_from_traccar(self):
        """
        Consulta las posiciones GPS registradas en Traccar para este vehículo
        en el intervalo del viaje y las almacena en transport.trip.point.
        """
        self.ensure_one()
        vehicle = self.vehicle_id
        if not vehicle.traccar_device_id:
            if vehicle.gps_imei:
                vehicle._create_device_in_traccar(raise_exception=False)
            if not vehicle.traccar_device_id:
                raise UserError(_("El vehículo %s no está vinculado con un dispositivo en Traccar.") % vehicle.name)

        url, user, password = vehicle._get_traccar_config()
        if not user or not password:
            raise UserError(_("Configure el usuario y contraseña de Traccar en Ajustes de Flota."))

        # Definir rango de consulta
        from_time = self.actual_start_time or self.scheduled_start_time - timedelta(minutes=10)
        to_time = self.actual_end_time or fields.Datetime.now() + timedelta(minutes=5)

        from_iso = fields.Datetime.to_datetime(from_time).strftime('%Y-%m-%dT%H:%M:%SZ')
        to_iso = fields.Datetime.to_datetime(to_time).strftime('%Y-%m-%dT%H:%M:%SZ')

        auth = (user, password)
        headers = {'Accept': 'application/json'}
        params = {
            'deviceId': vehicle.traccar_device_id,
            'from': from_iso,
            'to': to_iso
        }

        try:
            res = requests.get(f"{url}/api/positions", params=params, auth=auth, headers=headers, timeout=10)
            if res.status_code == 200:
                positions = res.json()
                if not positions:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _("Sin nuevas posiciones"),
                            'message': _("No se encontraron registros de posiciones en Traccar para el rango indicado."),
                            'type': 'warning',
                            'sticky': False,
                        }
                    }

                # Obtener timestamps ya existentes en este viaje para no duplicar
                existing_timestamps = set(self.point_ids.mapped('timestamp'))

                new_points = []
                coords_list = []
                for pos in positions:
                    fix_str = pos.get('fixTime') or pos.get('deviceTime')
                    if not fix_str:
                        continue
                    dt = parser.parse(fix_str)
                    dt_odoo = dt.strftime('%Y-%m-%d %H:%M:%S')

                    # Evitar duplicados
                    dt_field = fields.Datetime.to_datetime(dt_odoo)
                    if dt_field in existing_timestamps:
                        continue

                    lat = pos.get('latitude', 0.0)
                    lon = pos.get('longitude', 0.0)
                    speed_kmh = round(float(pos.get('speed', 0.0)) * 1.852, 2)

                    new_points.append((0, 0, {
                        'vehicle_id': vehicle.id,
                        'latitude': lat,
                        'longitude': lon,
                        'speed': speed_kmh,
                        'timestamp': dt_odoo,
                        'traccar_position_id': pos.get('id', 0),
                    }))
                    coords_list.append((lat, lon))

                if new_points:
                    self.write({'point_ids': new_points})
                    # Recalcular distancia acumulada del viaje
                    all_coords = [(p.latitude, p.longitude) for p in self.point_ids.sorted('timestamp')]
                    total_km = calculate_total_path_distance(all_coords)
                    self.write({'actual_distance': total_km})

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Sincronización Exitosa"),
                        'message': _("Se sincronizaron %d nuevas coordenadas GPS desde Traccar.") % len(new_points),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_("Error de Traccar (HTTP %s): %s") % (res.status_code, res.text))
        except requests.exceptions.RequestException as e:
            raise UserError(_("Error de comunicación con Traccar: %s") % str(e))

    def action_analyze_trip(self):
        """
        Motor de Detección Automática de Incumplimientos e Incidencias:
        1. Comprueba paradas visitadas y retrasos según radio y horarios.
        2. Comprueba desviaciones respecto al corredor geográfico de la ruta.
        3. Comprueba interrupciones de señal GPS.
        """
        self.ensure_one()
        points = self.point_ids.sorted('timestamp')
        if not points:
            _logger.info("El viaje %s no cuenta con puntos GPS registrados para analizar.", self.name)
            return

        # Limpiar incidencias anteriores autogeneradas
        self.incident_ids.unlink()

        incidents_to_create = []

        # 1. EVALUAR PARADAS / PUNTOS DE CONTROL
        for check in self.stop_check_ids:
            stop = check.stop_id
            target_lat = stop.latitude
            target_lon = stop.longitude
            radius = stop.proximity_radius or 50.0

            min_dist = float('inf')
            closest_point = False

            for p in points:
                d = haversine_distance(p.latitude, p.longitude, target_lat, target_lon)
                if d < min_dist:
                    min_dist = d
                    closest_point = p

            check.min_distance_meters = round(min_dist, 2)

            if min_dist <= radius and closest_point:
                check.actual_arrival_time = closest_point.timestamp
                # Verificar horario programado y retraso
                if check.scheduled_time:
                    delta_sec = (closest_point.timestamp - check.scheduled_time).total_seconds()
                    delay_m = delta_sec / 60.0
                    check.delay_minutes = max(0.0, round(delay_m, 1))

                    if delay_m > stop.time_tolerance:
                        check.status = 'delayed'
                        incidents_to_create.append({
                            'name': _("Retraso en parada: %s") % stop.name,
                            'trip_id': self.id,
                            'stop_id': stop.id,
                            'incident_type': 'delay',
                            'severity': 'medium',
                            'timestamp': closest_point.timestamp,
                            'delay_minutes': check.delay_minutes,
                            'latitude': closest_point.latitude,
                            'longitude': closest_point.longitude,
                            'description': _("Llegada registrada a las %s con un retraso de %.1f min (tolerancia: %d min).") % (
                                closest_point.timestamp, check.delay_minutes, stop.time_tolerance
                            )
                        })
                    else:
                        check.status = 'visited'
                else:
                    check.status = 'visited'
            else:
                # La parada fue omitida
                check.status = 'missed'
                incidents_to_create.append({
                    'name': _("Parada Omitida / No Visitada: %s") % stop.name,
                    'trip_id': self.id,
                    'stop_id': stop.id,
                    'incident_type': 'missed_stop',
                    'severity': 'high',
                    'timestamp': check.scheduled_time or fields.Datetime.now(),
                    'deviation_distance': min_dist,
                    'latitude': target_lat,
                    'longitude': target_lon,
                    'description': _("El vehículo no ingresó al radio de %d m de la parada %s (distancia más cercana: %.1f m).") % (
                        radius, stop.name, min_dist
                    )
                })

        # 2. EVALUAR DESVIACIONES DE RUTA
        # Si la ruta tiene coordenadas de referencia o usamos las coordenadas de las paradas
        reference_path = []
        if self.route_id.reference_coordinates:
            try:
                reference_path = json.loads(self.route_id.reference_coordinates)
            except Exception:
                pass
        if not reference_path and self.route_id.stop_ids:
            # Fallback: Usar la secuencia de paradas como ruta estimada
            reference_path = [(s.latitude, s.longitude) for s in self.route_id.stop_ids.sorted('sequence')]

        allowed_dev = self.route_id.allowed_deviation_meters or 150.0
        max_dev = 0.0
        worst_dev_point = False

        if reference_path:
            for p in points:
                dev = min_distance_to_path(p.latitude, p.longitude, reference_path)
                if dev > allowed_dev and dev > max_dev:
                    max_dev = dev
                    worst_dev_point = p

        if max_dev > allowed_dev and worst_dev_point:
            incidents_to_create.append({
                'name': _("Desviación del Trazado Oficial"),
                'trip_id': self.id,
                'incident_type': 'route_deviation',
                'severity': 'high',
                'timestamp': worst_dev_point.timestamp,
                'deviation_distance': round(max_dev, 2),
                'latitude': worst_dev_point.latitude,
                'longitude': worst_dev_point.longitude,
                'description': _("El vehículo se alejó a %.1f m de la ruta programada (tolerancia permitida: %.1f m).") % (
                    max_dev, allowed_dev
                )
            })

        # 3. EVALUAR INTERRUPCIONES DE SEÑAL GPS (Gaps > 10 minutos)
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            gap_seconds = (p2.timestamp - p1.timestamp).total_seconds()
            if gap_seconds > 600:  # Más de 10 minutos sin señal
                incidents_to_create.append({
                    'name': _("Interrupción / Pérdida de Señal GPS"),
                    'trip_id': self.id,
                    'incident_type': 'gps_lost',
                    'severity': 'medium',
                    'timestamp': p1.timestamp,
                    'latitude': p1.latitude,
                    'longitude': p1.longitude,
                    'description': _("Pérdida de reporte GPS de %.1f minutos entre las %s y %s.") % (
                        gap_seconds / 60.0, p1.timestamp, p2.timestamp
                    )
                })
                break

        # Crear incidencias
        if incidents_to_create:
            self.env['transport.trip.incident'].create(incidents_to_create)

        return True


class TransportTripStopCheck(models.Model):
    _name = 'transport.trip.stop.check'
    _description = 'Control de Paradas del Viaje'
    _order = 'sequence, id'

    trip_id = fields.Many2one(
        'transport.trip',
        string='Recorrido',
        required=True,
        ondelete='cascade'
    )
    stop_id = fields.Many2one(
        'transport.route.stop',
        string='Punto de Control / Parada',
        required=True
    )
    name = fields.Char(
        string='Nombre Parada',
        related='stop_id.name',
        store=True
    )
    sequence = fields.Integer(
        string='Orden',
        related='stop_id.sequence',
        store=True
    )
    scheduled_time = fields.Datetime(
        string='Horario Previsto'
    )
    actual_arrival_time = fields.Datetime(
        string='Llegada Registrada'
    )
    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('visited', 'Cumplida a Tiempo'),
        ('delayed', 'Cumplida con Retraso'),
        ('missed', 'Omitida / Incumplida')
    ], string='Estado de Cumplimiento', default='pending', required=True)

    min_distance_meters = fields.Float(
        string='Distancia Mínima al Punto (m)',
        digits=(8, 2),
        help="Distancia más cercana a la que pasó el vehículo respecto a la parada."
    )
    delay_minutes = fields.Float(
        string='Retraso Registrado (min)',
        digits=(6, 1)
    )


class TransportTripPoint(models.Model):
    _name = 'transport.trip.point'
    _description = 'Punto de Coordenada GPS de Recorrido'
    _order = 'timestamp asc, id asc'

    trip_id = fields.Many2one(
        'transport.trip',
        string='Recorrido',
        required=True,
        ondelete='cascade',
        index=True
    )
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo',
        required=True,
        index=True
    )
    latitude = fields.Float(
        string='Latitud',
        digits=(10, 7),
        required=True
    )
    longitude = fields.Float(
        string='Longitud',
        digits=(10, 7),
        required=True
    )
    speed = fields.Float(
        string='Velocidad (km/h)',
        digits=(6, 2),
        default=0.0
    )
    timestamp = fields.Datetime(
        string='Fecha y Hora GPS',
        required=True,
        index=True
    )
    traccar_position_id = fields.Integer(
        string='ID Posición Traccar',
        index=True
    )
    is_valid = fields.Boolean(
        string='¿Registro Válido?',
        default=True
    )

    _sql_constraints = [
        ('trip_timestamp_unique', 'unique(trip_id, timestamp)', 'No se permiten registros duplicados en el mismo recorrido.')
    ]

