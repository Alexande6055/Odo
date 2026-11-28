# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class TransportTripIncident(models.Model):
    _name = 'transport.trip.incident'
    _description = 'Incidencia o Incumplimiento de Recorrido'
    _order = 'timestamp desc, id desc'

    name = fields.Char(
        string='Título de la Incidencia',
        required=True
    )
    # Filtros auxiliares combinables (no se guardan en BD) para acotar la búsqueda de recorridos
    filter_trip_date = fields.Date(
        string='Filtrar por Fecha',
        store=False,
        help="Opcional: filtra los recorridos disponibles por fecha."
    )
    filter_vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Filtrar por Vehículo',
        store=False,
        help="Opcional: filtra los recorridos disponibles por bus/vehículo."
    )
    filter_driver_id = fields.Many2one(
        'res.partner',
        string='Filtrar por Conductor',
        store=False,
        help="Opcional: filtra los recorridos disponibles por conductor."
    )

    trip_id = fields.Many2one(
        'transport.trip',
        string='Recorrido Asociado',
        required=True,
        domain="[('state', 'in', ('in_progress', 'completed'))]",
        ondelete='cascade'
    )
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo',
        related='trip_id.vehicle_id',
        store=True,
        index=True
    )
    route_id = fields.Many2one(
        'transport.route',
        string='Ruta',
        related='trip_id.route_id',
        store=True,
        index=True
    )
    stop_id = fields.Many2one(
        'transport.route.stop',
        string='Punto de Control Afectado',
        help="Parada o punto de control relacionado con el incumplimiento, si aplica."
    )
    incident_type = fields.Selection([
        ('delay', 'Retraso de Horario'),
        ('missed_stop', 'Incumplimiento de Parada (Omitida)'),
        ('route_deviation', 'Desviación de Ruta'),
        ('incomplete_trip', 'Recorrido Incompleto'),
        ('gps_lost', 'Interrupción de Señal GPS'),
        ('accident', 'Accidente / Avería'),
        ('other', 'Otra Incidencia')
    ], string='Tipo de Incidencia', required=True, default='delay', index=True)

    severity = fields.Selection([
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta / Crítica')
    ], string='Severidad', required=True, default='medium')

    timestamp = fields.Datetime(
        string='Fecha y Hora del Evento',
        default=fields.Datetime.now,
        required=True,
        index=True
    )
    description = fields.Text(
        string='Detalle / Explicación del Incumplimiento'
    )
    delay_minutes = fields.Float(
        string='Tiempo de Retraso (min)',
        digits=(6, 1),
        help="Minutos de retraso cuantificados"
    )
    deviation_distance = fields.Float(
        string='Distancia de Desvío (metros)',
        digits=(8, 2),
        help="Distancia máxima fuera del corredor autorizado"
    )
    latitude = fields.Float(
        string='Latitud del Evento',
        digits=(10, 7)
    )
    longitude = fields.Float(
        string='Longitud del Evento',
        digits=(10, 7)
    )

    @api.onchange('filter_trip_date', 'filter_vehicle_id', 'filter_driver_id')
    def _onchange_trip_filters(self):
        domain = [('state', 'in', ('in_progress', 'completed'))]
        if self.filter_trip_date:
            domain.append(('date', '=', self.filter_trip_date))
        if self.filter_vehicle_id:
            domain.append(('vehicle_id', '=', self.filter_vehicle_id.id))
        if self.filter_driver_id:
            domain.append(('driver_id', '=', self.filter_driver_id.id))

        if self.trip_id:
            matches = True
            if self.filter_trip_date and self.trip_id.date != self.filter_trip_date:
                matches = False
            if self.filter_vehicle_id and self.trip_id.vehicle_id != self.filter_vehicle_id:
                matches = False
            if self.filter_driver_id and self.trip_id.driver_id != self.filter_driver_id:
                matches = False
            if not matches:
                self.trip_id = False
                self.stop_id = False

        return {'domain': {'trip_id': domain}}

    @api.onchange('trip_id')
    def _onchange_trip_id(self):
        if self.trip_id and self.stop_id and self.stop_id.route_id != self.trip_id.route_id:
            self.stop_id = False
        if self.trip_id and self.trip_id.route_id:
            return {'domain': {'stop_id': [('route_id', '=', self.trip_id.route_id.id)]}}
        return {'domain': {'stop_id': []}}

    @api.constrains('trip_id', 'stop_id')
    def _check_incident_trip_and_stop(self):
        for inc in self:
            if inc.trip_id and inc.trip_id.state not in ('in_progress', 'completed'):
                raise ValidationError(
                    _("Solo se pueden registrar incidencias sobre recorridos En Curso o Completados (el recorrido %s está en estado %s).")
                    % (inc.trip_id.name, inc.trip_id.state)
                )
            if inc.stop_id and inc.trip_id and inc.stop_id.route_id != inc.trip_id.route_id:
                raise ValidationError(
                    _("La parada '%s' no pertenece a la ruta del recorrido seleccionado.") % inc.stop_id.name
                )

    @api.constrains('latitude', 'longitude', 'delay_minutes', 'deviation_distance')
    def _check_incident_values(self):
        for inc in self:
            if inc.latitude and (inc.latitude < -90.0 or inc.latitude > 90.0):
                raise ValidationError(_("La latitud del evento debe estar entre -90 y 90 grados."))
            if inc.longitude and (inc.longitude < -180.0 or inc.longitude > 180.0):
                raise ValidationError(_("La longitud del evento debe estar entre -180 y 180 grados."))
            if (inc.delay_minutes or 0.0) < 0:
                raise ValidationError(_("El tiempo de retraso no puede ser negativo."))
            if (inc.deviation_distance or 0.0) < 0:
                raise ValidationError(_("La distancia de desvío no puede ser negativa."))

