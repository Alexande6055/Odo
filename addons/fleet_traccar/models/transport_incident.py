# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class TransportTripIncident(models.Model):
    _name = 'transport.trip.incident'
    _description = 'Incidencia o Incumplimiento de Recorrido'
    _order = 'timestamp desc, id desc'

    name = fields.Char(
        string='Título de la Incidencia',
        required=True
    )
    trip_id = fields.Many2one(
        'transport.trip',
        string='Recorrido Asociado',
        required=True,
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

