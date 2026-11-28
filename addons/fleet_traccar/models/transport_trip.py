# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime, time as dt_time, timedelta
from dateutil import parser
import pytz
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
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
        string='Conductor Asignado',
        index=True
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
        string='Salida Programada (Fecha/Hora)',
        required=True,
        default=lambda self: fields.Datetime.now() + timedelta(minutes=5),
        index=True
    )
    scheduled_end_time = fields.Datetime(
        string='Llegada Programada (Fecha/Hora)',
        required=True,
        default=lambda self: fields.Datetime.now() + timedelta(minutes=35)
    )
    actual_start_time = fields.Datetime(
        string='Salida Real Registrada (Fecha/Hora)'
    )
    actual_end_time = fields.Datetime(
        string='Llegada Real Registrada (Fecha/Hora)'
    )

    # Campos de solo hora (HH:MM) para captura limpia sin fecha en formularios
    scheduled_start_hour = fields.Float(
        string='Salida Programada',
        compute='_compute_trip_hours',
        inverse='_inverse_scheduled_start_hour',
        help='Hora de salida programada en formato 24h (HH:MM), asociada a la Fecha del Recorrido.'
    )
    scheduled_end_hour = fields.Float(
        string='Llegada Programada',
        compute='_compute_trip_hours',
        inverse='_inverse_scheduled_end_hour',
        help='Hora de llegada programada en formato 24h (HH:MM), asociada a la Fecha del Recorrido.'
    )
    actual_start_hour = fields.Float(
        string='Salida Real Registrada',
        compute='_compute_trip_hours',
        inverse='_inverse_actual_start_hour',
        help='Hora real de salida en formato 24h (HH:MM).'
    )
    actual_end_hour = fields.Float(
        string='Llegada Real Registrada',
        compute='_compute_trip_hours',
        inverse='_inverse_actual_end_hour',
        help='Hora real de llegada en formato 24h (HH:MM).'
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

    trip_direction = fields.Selection([
        ('outbound', 'Ida / Salida'),
        ('inbound', 'Regreso / Retorno'),
    ], string='Sentido del Recorrido', default='outbound', required=True, index=True)

    estimated_distance = fields.Float(
        string='Distancia Estimada (km)',
        compute='_compute_estimated_distance',
        store=True,
        digits=(6, 2)
    )

    @api.depends('route_id', 'trip_direction', 'route_id.outbound_distance', 'route_id.return_distance', 'route_id.estimated_distance')
    def _compute_estimated_distance(self):
        for trip in self:
            if not trip.route_id:
                trip.estimated_distance = 0.0
            elif trip.trip_direction == 'inbound':
                trip.estimated_distance = trip.route_id.return_distance or trip.route_id.estimated_distance
            else:
                trip.estimated_distance = trip.route_id.outbound_distance or trip.route_id.estimated_distance
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
    trip_map_html = fields.Html(
        string='Mapa Interactivo del Recorrido',
        compute='_compute_trip_map_html',
        sanitize=False
    )
    notes = fields.Text(string='Observaciones')

    def _apply_hour_vals(self, vals, default_date=None):
        """Convierte campos de solo hora (HH:MM) a Datetime UTC antes de crear/escribir."""
        trip_date = vals.get('date') or default_date or fields.Date.context_today(self)
        if isinstance(trip_date, str):
            trip_date = fields.Date.from_string(trip_date)
        hour_map = [
            ('scheduled_start_hour', 'scheduled_start_time', True),
            ('scheduled_end_hour', 'scheduled_end_time', True),
            ('actual_start_hour', 'actual_start_time', False),
            ('actual_end_hour', 'actual_end_time', False),
        ]
        for h_field, dt_field, always_set in hour_map:
            if h_field in vals and dt_field not in vals:
                h_val = vals[h_field]
                if always_set or (h_val and h_val > 0.0):
                    vals[dt_field] = self._date_and_hour_to_utc_datetime(trip_date, h_val or 0.0)
                else:
                    vals[dt_field] = False
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transport.trip') or _('Nuevo')
            self._apply_hour_vals(vals)
        records = super(TransportTrip, self).create(vals_list)
        for record in records:
            record._initialize_stop_checks()
        return records

    def write(self, vals):
        if any(k in vals for k in ('scheduled_start_hour', 'scheduled_end_hour', 'actual_start_hour', 'actual_end_hour')):
            for rec in self:
                rec_vals = dict(vals)
                rec._apply_hour_vals(rec_vals, default_date=rec.date)
                super(TransportTrip, rec).write(rec_vals)
            return True
        return super(TransportTrip, self).write(vals)

    @api.depends('point_ids', 'stop_check_ids', 'incident_ids')
    def _compute_counts(self):
        for trip in self:
            trip.point_count = len(trip.point_ids)
            trip.stop_check_count = len(trip.stop_check_ids)
            trip.incident_count = len(trip.incident_ids)

    @api.depends('route_id', 'vehicle_id', 'vehicle_id.traccar_device_id', 'vehicle_id.gps_imei', 'stop_check_ids', 'stop_check_ids.status', 'point_ids', 'incident_ids')
    def _compute_trip_map_html(self):
        import urllib.parse
        import json
        from .geo_utils import get_configured_map_web_url
        map_base = get_configured_map_web_url(self.env)
        ICP = self.env['ir.config_parameter'].sudo()
        user = (ICP.get_param('fleet_traccar.user') or '').strip()
        password = ICP.get_param('fleet_traccar.password') or ''

        for trip in self:
            query_params = {'compact': 'true'}
            if user:
                query_params['user'] = user
            if password:
                query_params['pass'] = password

            if trip.vehicle_id.traccar_device_id:
                query_params['deviceId'] = str(trip.vehicle_id.traccar_device_id)
            elif trip.vehicle_id.gps_imei:
                query_params['imei'] = str(trip.vehicle_id.gps_imei)

            if trip.route_id:
                query_params['routeName'] = trip.route_id.name or ''
                stops_data = []
                stops = trip.stop_check_ids.mapped('stop_id') if trip.stop_check_ids else trip.route_id.stop_ids
                for s in stops.sorted('sequence'):
                    sc = trip.stop_check_ids.filtered(lambda c: c.stop_id == s)
                    stops_data.append({
                        'name': s.name,
                        'seq': s.sequence,
                        'lat': s.latitude,
                        'lon': s.longitude,
                        'status': sc.status if sc else 'pending',
                        'delay': sc.delay_minutes if sc else 0,
                        'schedTime': sc.scheduled_time.strftime('%H:%M') if sc and sc.scheduled_time else f"+{s.expected_offset_minutes}m",
                        'actualTime': sc.actual_arrival_time.strftime('%H:%M') if sc and sc.actual_arrival_time else '',
                    })
                if stops_data:
                    query_params['stops'] = json.dumps(stops_data)

            if trip.state in ('in_progress', 'completed'):
                query_params['autoRoute'] = 'true'

            map_url = f"{map_base}/?{urllib.parse.urlencode(query_params)}"
            full_url = map_url.replace('&compact=true', '').replace('?compact=true', '')
            route_label = trip.route_id.name or 'Recorrido en Curso'
            vehicle_label = trip.vehicle_id.name or 'Bus Universitario'

            trip.trip_map_html = f'''
                <div class="card shadow border-0 my-2 rounded-3 overflow-hidden">
                    <div class="card-header text-white d-flex justify-content-between align-items-center py-2 px-3" style="background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);">
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge rounded-pill bg-info text-dark fw-bold px-2 py-1">
                                <i class="fa fa-map-marker me-1"></i>Micro-Sistema GPS
                            </span>
                            <span class="fw-bold text-white small">
                                {route_label} • <span class="text-cyan">{vehicle_label}</span>
                            </span>
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <a href="{full_url}" target="_blank" class="btn btn-sm btn-outline-info text-white">
                                <i class="fa fa-external-link me-1"></i>Pantalla Completa
                            </a>
                        </div>
                    </div>
                    <div class="card-body p-0 position-relative" style="height: 560px; background: #0f172a;">
                        <iframe src="{map_url}" 
                                style="width: 100%; height: 560px; border: none; display: block;" 
                                allow="geolocation">
                        </iframe>
                    </div>
                </div>
            '''

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id and self.vehicle_id.driver_id:
            self.driver_id = self.vehicle_id.driver_id

    def action_view_points(self):
        self.ensure_one()
        return {
            'name': _('Coordenadas GPS del Viaje'),
            'type': 'ir.actions.act_window',
            'res_model': 'transport.trip.point',
            'view_mode': 'tree,form',
            'domain': [('trip_id', '=', self.id)],
            'context': {'default_trip_id': self.id},
        }

    def action_view_incidents(self):
        self.ensure_one()
        return {
            'name': _('Incidencias del Recorrido'),
            'type': 'ir.actions.act_window',
            'res_model': 'transport.trip.incident',
            'view_mode': 'tree,form,graph',
            'domain': [('trip_id', '=', self.id)],
            'context': {'default_trip_id': self.id},
        }

    def action_view_stops(self):
        self.ensure_one()
        return {
            'name': _('Puntos de Control del Viaje'),
            'type': 'ir.actions.act_window',
            'res_model': 'transport.trip.stop.check',
            'view_mode': 'tree,form',
            'domain': [('trip_id', '=', self.id)],
            'context': {'default_trip_id': self.id},
        }

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

    def _get_user_tz(self):
        tz_name = self.env.user.tz or self.env.context.get('tz') or 'America/Guayaquil'
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.timezone('America/Guayaquil')

    def _datetime_to_local_hour(self, dt_val):
        if not dt_val:
            return 0.0
        dt_utc = pytz.UTC.localize(fields.Datetime.to_datetime(dt_val))
        local_dt = dt_utc.astimezone(self._get_user_tz())
        return round(local_dt.hour + (local_dt.minute / 60.0), 4)

    def _date_and_hour_to_utc_datetime(self, trip_date, hour_float):
        if not trip_date:
            trip_date = fields.Date.context_today(self)
        if hour_float < 0.0 or hour_float >= 24.0:
            raise ValidationError(_("Las horas deben estar en el rango de 00:00 a 23:59."))
        total_minutes = int(round(hour_float * 60))
        hours = min(total_minutes // 60, 23)
        minutes = total_minutes % 60
        naive_local = datetime.combine(trip_date, dt_time(hours, minutes))
        local_dt = self._get_user_tz().localize(naive_local)
        return local_dt.astimezone(pytz.UTC).replace(tzinfo=None)

    @api.depends('scheduled_start_time', 'scheduled_end_time', 'actual_start_time', 'actual_end_time')
    def _compute_trip_hours(self):
        for trip in self:
            trip.scheduled_start_hour = trip._datetime_to_local_hour(trip.scheduled_start_time) if trip.scheduled_start_time else 0.0
            trip.scheduled_end_hour = trip._datetime_to_local_hour(trip.scheduled_end_time) if trip.scheduled_end_time else 0.0
            trip.actual_start_hour = trip._datetime_to_local_hour(trip.actual_start_time) if trip.actual_start_time else 0.0
            trip.actual_end_hour = trip._datetime_to_local_hour(trip.actual_end_time) if trip.actual_end_time else 0.0

    def _inverse_scheduled_start_hour(self):
        for trip in self:
            if trip.date:
                trip.scheduled_start_time = trip._date_and_hour_to_utc_datetime(trip.date, trip.scheduled_start_hour or 0.0)

    def _inverse_scheduled_end_hour(self):
        for trip in self:
            if trip.date:
                trip.scheduled_end_time = trip._date_and_hour_to_utc_datetime(trip.date, trip.scheduled_end_hour or 0.0)

    def _inverse_actual_start_hour(self):
        for trip in self:
            if trip.actual_start_hour and trip.actual_start_hour > 0.0:
                trip.actual_start_time = trip._date_and_hour_to_utc_datetime(trip.date, trip.actual_start_hour)
            elif not trip.actual_start_hour and trip.state == 'draft':
                trip.actual_start_time = False

    def _inverse_actual_end_hour(self):
        for trip in self:
            if trip.actual_end_hour and trip.actual_end_hour > 0.0:
                trip.actual_end_time = trip._date_and_hour_to_utc_datetime(trip.date, trip.actual_end_hour)
            elif not trip.actual_end_hour and trip.state in ('draft', 'in_progress'):
                trip.actual_end_time = False

    @api.onchange('date', 'route_id', 'trip_direction', 'scheduled_start_hour')
    def _onchange_route_schedule(self):
        if self.date and self.scheduled_start_hour is not None:
            if 0.0 <= self.scheduled_start_hour < 24.0:
                start_utc = self._date_and_hour_to_utc_datetime(self.date, self.scheduled_start_hour)
                self.scheduled_start_time = start_utc
                if self.route_id:
                    dur = self.route_id.return_duration if self.trip_direction == 'inbound' else self.route_id.estimated_duration
                    end_utc = start_utc + timedelta(minutes=dur or 25.0)
                    self.scheduled_end_time = end_utc
                    self.scheduled_end_hour = self._datetime_to_local_hour(end_utc)
                elif self.scheduled_end_hour and 0.0 <= self.scheduled_end_hour < 24.0:
                    self.scheduled_end_time = self._date_and_hour_to_utc_datetime(self.date, self.scheduled_end_hour)

    @api.constrains('date', 'scheduled_start_time', 'scheduled_end_time', 'actual_start_time', 'actual_end_time', 'state')
    def _check_trip_dates_and_hours(self):
        if self.env.context.get('skip_date_validation'):
            return
        today = fields.Date.context_today(self)
        now_utc = fields.Datetime.now()
        for trip in self:
            if trip.state == 'draft' and trip.date and trip.date < today:
                raise ValidationError(
                    _("No se puede programar un recorrido con una fecha anterior a hoy (%s).")
                    % today.strftime('%d/%m/%Y')
                )

            if trip.scheduled_start_time and trip.scheduled_end_time:
                if trip.scheduled_end_time <= trip.scheduled_start_time:
                    raise ValidationError(
                        _("La hora de Llegada Programada debe ser posterior a la hora de Salida Programada.")
                    )

            if trip.state == 'draft' and trip.date == today and trip.scheduled_start_time:
                if trip.scheduled_start_time < (now_utc - timedelta(minutes=2)):
                    raise ValidationError(
                        _("La hora de Salida Programada no puede ser anterior a la hora actual para un recorrido de hoy.")
                    )

            if trip.actual_start_time and trip.actual_end_time:
                if trip.actual_end_time < trip.actual_start_time:
                    raise ValidationError(
                        _("La hora de Llegada Real no puede ser anterior a la hora de Salida Real.")
                    )

    @api.constrains('vehicle_id', 'scheduled_start_time', 'scheduled_end_time', 'state')
    def _check_vehicle_schedule_overlap(self):
        for trip in self:
            if trip.state not in ('draft', 'in_progress') or not trip.vehicle_id:
                continue
            if not trip.scheduled_start_time or not trip.scheduled_end_time:
                continue
            overlapping = self.search([
                ('id', '!=', trip.id),
                ('vehicle_id', '=', trip.vehicle_id.id),
                ('state', 'in', ('draft', 'in_progress')),
                ('scheduled_start_time', '<', trip.scheduled_end_time),
                ('scheduled_end_time', '>', trip.scheduled_start_time),
            ], limit=1)
            if overlapping:
                raise ValidationError(
                    _("El vehículo %s ya tiene asignado el recorrido %s en un horario superpuesto.")
                    % (trip.vehicle_id.display_name, overlapping.name)
                )

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
            elif trip.delay_minutes > 0.0 or bool(trip.incident_ids.filtered(lambda i: i.incident_type == 'delay')):
                trip.compliance_status = 'delayed'
            else:
                trip.compliance_status = 'compliant'

    def action_create_return_trip(self):
        """
        Genera automáticamente el tramo de retorno (o siguiente tramo de ida) para la misma ruta,
        calculando la hora de salida con el tiempo de espera en cabecera (layover_duration).
        """
        self.ensure_one()
        next_dir = 'inbound' if self.trip_direction == 'outbound' else 'outbound'
        dir_name = _('Retorno / Regreso') if next_dir == 'inbound' else _('Salida / Ida')

        base_time = self.actual_end_time or self.scheduled_end_time or fields.Datetime.now()
        layover = self.route_id.layover_duration if self.route_id.layover_duration is not False else 15.0
        start_next = base_time + timedelta(minutes=layover)
        dur = self.route_id.return_duration if next_dir == 'inbound' else self.route_id.estimated_duration
        end_next = start_next + timedelta(minutes=dur or 25.0)

        new_trip = self.create({
            'route_id': self.route_id.id,
            'trip_direction': next_dir,
            'vehicle_id': self.vehicle_id.id,
            'driver_id': self.driver_id.id if self.driver_id else False,
            'date': start_next.date(),
            'scheduled_start_time': start_next,
            'scheduled_end_time': end_next,
            'state': 'draft',
        })

        return {
            'name': _('Recorrido de %s Creado') % dir_name,
            'type': 'ir.actions.act_window',
            'res_model': 'transport.trip',
            'res_id': new_trip.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_start_trip(self):
        """Inicia el recorrido formalmente con validaciones previas."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Solo se pueden iniciar recorridos en estado Borrador / Programado."))
        today = fields.Date.context_today(self)
        if self.date and self.date < today:
            raise UserError(
                _("No se puede iniciar un recorrido programado para una fecha pasada (%s).")
                % self.date.strftime('%d/%m/%Y')
            )
        if self.scheduled_start_time and self.scheduled_end_time and self.scheduled_end_time <= self.scheduled_start_time:
            raise UserError(_("La hora de Llegada Programada debe ser posterior a la Salida Programada."))
        vals = {'state': 'in_progress'}
        if not self.actual_start_time:
            vals['actual_start_time'] = fields.Datetime.now()
        if not self.stop_check_ids:
            self._initialize_stop_checks()
        self.write(vals)

    def action_complete_trip(self):
        """Finaliza el recorrido y dispara el análisis automático."""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Solo se pueden finalizar recorridos que estén En Curso."))
        vals = {'state': 'completed'}
        end_dt = self.actual_end_time or fields.Datetime.now()
        if self.actual_start_time and end_dt < self.actual_start_time:
            raise UserError(_("La hora de Llegada Real no puede ser anterior a la Salida Real."))
        if not self.actual_end_time:
            vals['actual_end_time'] = end_dt
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

                    if delay_m > 0:
                        check.status = 'delayed'
                        # Regla: Retraso <= 3 min es incidencia Baja, > 3 min es incidencia Media (sin margen de tolerancia)
                        if delay_m <= 3.0:
                            sev = 'low'
                            sev_label = _("Baja (≤ 3 min)")
                        else:
                            sev = 'medium'
                            sev_label = _("Media (> 3 min)")

                        incidents_to_create.append({
                            'name': _("Retraso en parada: %s (%.1f min - %s)") % (stop.name, check.delay_minutes, sev_label),
                            'trip_id': self.id,
                            'stop_id': stop.id,
                            'incident_type': 'delay',
                            'severity': sev,
                            'timestamp': closest_point.timestamp,
                            'delay_minutes': check.delay_minutes,
                            'latitude': closest_point.latitude,
                            'longitude': closest_point.longitude,
                            'description': _("Llegada registrada a las %s con un retraso de %.1f min respecto al horario previsto (%s). Incidencia clasificada como severidad %s.") % (
                                closest_point.timestamp, check.delay_minutes, check.scheduled_time, sev_label
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

        # 1.1 EVALUAR RETRASO AL COMPLETAR EL RECORRIDO (LLEGADA A DESTINO FINAL)
        trip_end_time = self.actual_end_time or (points[-1].timestamp if points else False)
        if trip_end_time and self.scheduled_end_time:
            end_delta_sec = (trip_end_time - self.scheduled_end_time).total_seconds()
            end_delay_m = end_delta_sec / 60.0
            if end_delay_m > 0:
                if end_delay_m <= 3.0:
                    trip_sev = 'low'
                    trip_sev_label = _("Baja (≤ 3 min)")
                else:
                    trip_sev = 'medium'
                    trip_sev_label = _("Media (> 3 min)")

                incidents_to_create.append({
                    'name': _("Retraso en llegada a destino final (%.1f min - %s)") % (round(end_delay_m, 1), trip_sev_label),
                    'trip_id': self.id,
                    'incident_type': 'delay',
                    'severity': trip_sev,
                    'timestamp': trip_end_time,
                    'delay_minutes': round(end_delay_m, 1),
                    'latitude': points[-1].latitude if points else False,
                    'longitude': points[-1].longitude if points else False,
                    'description': _("El recorrido completó su destino a las %s con un retraso total de %.1f min respecto a la llegada programada (%s). Incidencia clasificada como severidad %s.") % (
                        trip_end_time, round(end_delay_m, 1), self.scheduled_end_time, trip_sev_label
                    )
                })

        # 2. EVALUAR DESVIACIONES DE RUTA SEGÚN SENTIDO (IDA O REGRESO)
        reference_path = []
        if self.trip_direction == 'inbound' and self.route_id.return_coordinates:
            try:
                reference_path = json.loads(self.route_id.return_coordinates)
            except Exception:
                reference_path = []
        elif self.route_id.reference_coordinates:
            try:
                reference_path = json.loads(self.route_id.reference_coordinates)
            except Exception:
                reference_path = []
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
        string='Horario Previsto (Fecha/Hora)'
    )
    scheduled_hour = fields.Float(
        string='Horario Previsto',
        compute='_compute_scheduled_hour',
        inverse='_inverse_scheduled_hour',
        help='Hora prevista de paso en formato 24h (HH:MM).'
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

    @api.depends('scheduled_time')
    def _compute_scheduled_hour(self):
        for check in self:
            if check.scheduled_time and check.trip_id:
                check.scheduled_hour = check.trip_id._datetime_to_local_hour(check.scheduled_time)
            else:
                check.scheduled_hour = 0.0

    def _inverse_scheduled_hour(self):
        for check in self:
            if check.trip_id:
                trip_date = check.trip_id.date or fields.Date.context_today(check)
                check.scheduled_time = check.trip_id._date_and_hour_to_utc_datetime(trip_date, check.scheduled_hour or 0.0)


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

