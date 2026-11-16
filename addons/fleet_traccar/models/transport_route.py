# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class TransportRoute(models.Model):
    _name = 'transport.route'
    _description = 'Ruta de Transporte Universitario'
    _order = 'name asc'

    name = fields.Char(
        string='Nombre de la Ruta',
        required=True,
        help="Ej: Campus Huachi - Campus Ingahurco"
    )
    code = fields.Char(
        string='Código de Ruta',
        required=True,
        copy=False,
        help="Identificador único (ej: UTA-R01)"
    )
    origin = fields.Char(
        string='Punto de Origen (Ida)',
        default='Tomado automáticamente del 1er vértice de ida',
        help="Lugar de partida de ida. Se toma automáticamente del primer vértice trazado en el mapa."
    )
    destination = fields.Char(
        string='Punto de Destino (Llegada Ida)',
        default='Tomado automáticamente del último vértice de ida',
        help="Lugar de llegada de ida. Se toma automáticamente del último vértice trazado en el mapa."
    )
    origin_return = fields.Char(
        string='Origen del Retorno',
        default='Tomado automáticamente del 1er vértice de retorno',
        help="Lugar de partida del tramo de regreso."
    )
    destination_return = fields.Char(
        string='Destino del Retorno',
        default='Tomado automáticamente del último vértice de retorno',
        help="Lugar de llegada final del tramo de regreso."
    )
    outbound_distance = fields.Float(
        string='Distancia de Ida (km)',
        digits=(6, 2),
        default=0.0,
        help="Distancia calculada del tramo de ida en kilómetros."
    )
    return_distance = fields.Float(
        string='Distancia de Retorno (km)',
        digits=(6, 2),
        default=0.0,
        help="Distancia calculada del tramo de regreso en kilómetros."
    )
    estimated_distance = fields.Float(
        string='Distancia Total Ida + Retorno (km)',
        digits=(6, 2),
        compute='_compute_total_distance',
        store=True,
        help="Distancia total acumulada de ida y regreso."
    )
    estimated_duration = fields.Float(
        string='Duración Estimada Ida (min)',
        digits=(6, 1),
        default=25.0,
        help="Tiempo previsto de viaje para el tramo de ida en minutos. NOTA: Este tiempo ya debe comprender el tiempo total estimado de las paradas intermedias."
    )
    return_duration = fields.Float(
        string='Duración Estimada Retorno (min)',
        digits=(6, 1),
        default=25.0,
        help="Tiempo previsto de viaje para el tramo de regreso en minutos. NOTA: Este tiempo ya debe comprender el tiempo total estimado de las paradas intermedias."
    )
    layover_duration = fields.Float(
        string='Tiempo de Espera en Cabecera (min)',
        default=15.0,
        digits=(5, 1),
        help="Tiempo estimado de espera o regulación en el punto final antes de iniciar el tramo de regreso (opcional)."
    )
    allowed_deviation_meters = fields.Float(
        string='Tolerancia de Desvío (metros)',
        default=150.0,
        help="Distancia máxima permitida en metros fuera del corredor de la ruta antes de disparar una alarma de desviación."
    )
    description = fields.Text(
        string='Descripción / Notas'
    )
    active = fields.Boolean(
        string='Activo',
        default=True
    )
    color = fields.Integer(
        string='Color'
    )
    reference_coordinates = fields.Text(
        string='Coordenadas del Trazado de Ida',
        help="Pares de coordenadas lat,lon del tramo de ida (Línea Azul)."
    )
    return_coordinates = fields.Text(
        string='Coordenadas del Trazado de Regreso',
        help="Pares de coordenadas lat,lon del tramo de regreso (Línea Naranja)."
    )
    route_map_html = fields.Html(
        string='Mapa Interactivo de la Ruta',
        compute='_compute_route_map_html',
        sanitize=False
    )
    stop_ids = fields.One2many(
        'transport.route.stop',
        'route_id',
        string='Puntos de Control / Paradas'
    )
    stop_count = fields.Integer(
        string='Total Paradas',
        compute='_compute_counts'
    )
    trip_ids = fields.One2many(
        'transport.trip',
        'route_id',
        string='Recorridos Realizados'
    )
    trip_count = fields.Integer(
        string='Total Recorridos',
        compute='_compute_counts'
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'El código de ruta debe ser único.')
    ]

    @api.depends('outbound_distance', 'return_distance')
    def _compute_total_distance(self):
        for route in self:
            route.estimated_distance = round((route.outbound_distance or 0.0) + (route.return_distance or 0.0), 2)

    @api.depends('stop_ids', 'name', 'reference_coordinates', 'return_coordinates')
    def _compute_route_map_html(self):
        for route in self:
            if not route.id:
                route.route_map_html = '<div class="alert alert-info py-2 px-3 small">Guarde la ruta para activar el diseñador interactivo de trazado y paradas.</div>'
                continue

            editor_url = f"/transport/route/map_editor/{route.id}"
            route_title = route.name or 'Trazado Oficial'
            route.route_map_html = f'''
                <div class="card shadow-sm border-0 my-2 rounded-3 overflow-hidden">
                    <div class="card-header text-white d-flex justify-content-between align-items-center py-2 px-3" style="background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);">
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge rounded-pill bg-primary px-2 py-1">
                                <i class="fa fa-pencil me-1"></i>Diseñador Interactivo de Trazado
                            </span>
                            <span class="fw-bold text-white small">{route_title}</span>
                        </div>
                        <a href="{editor_url}" target="_blank" class="btn btn-sm btn-outline-info text-white">
                            <i class="fa fa-external-link me-1"></i>Abrir en Pantalla Completa
                        </a>
                    </div>
                    <div class="card-body p-0 position-relative" style="height: 540px; background: #0f172a;">
                        <iframe src="{editor_url}" 
                                style="width: 100%; height: 540px; border: none; display: block;" 
                                allow="geolocation">
                        </iframe>
                    </div>
                </div>
            '''

    def action_open_map_editor(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/transport/route/map_editor/{self.id}',
            'target': 'new',
        }

    @api.depends('stop_ids', 'trip_ids')
    def _compute_counts(self):
        for route in self:
            route.stop_count = len(route.stop_ids)
            route.trip_count = len(route.trip_ids)

    def action_view_stops(self):
        self.ensure_one()
        return {
            'name': _('Puntos de Control / Paradas'),
            'type': 'ir.actions.act_window',
            'res_model': 'transport.route.stop',
            'view_mode': 'tree,form',
            'domain': [('route_id', '=', self.id)],
            'context': {'default_route_id': self.id},
        }


class TransportRouteStop(models.Model):
    _name = 'transport.route.stop'
    _description = 'Punto de Control / Parada de Ruta'
    _order = 'route_id, sequence, id'

    name = fields.Char(
        string='Nombre de la Parada',
        required=True,
        help="Ej: Parada Mall de los Andes"
    )
    sequence = fields.Integer(
        string='Orden / Secuencia',
        default=10
    )
    route_id = fields.Many2one(
        'transport.route',
        string='Ruta Perteneciente',
        required=True,
        ondelete='cascade'
    )
    latitude = fields.Float(
        string='Latitud GPS',
        digits=(10, 7),
        required=True
    )
    longitude = fields.Float(
        string='Longitud GPS',
        digits=(10, 7),
        required=True
    )
    expected_offset_minutes = fields.Integer(
        string='Tiempo Estimado de Llegada (+min)',
        default=0,
        help="Minutos estimados transcurridos desde la salida del viaje para llegar a este punto."
    )
    proximity_radius = fields.Float(
        string='Radio de Proximidad (m)',
        default=50.0,
        help="Radio en metros alrededor del punto para confirmar automáticamente que el bus pasó por la parada."
    )
    time_tolerance = fields.Integer(
        string='Tolerancia de Retraso (min)',
        default=5,
        help="Margen de minutos sobre el horario previsto antes de considerar la llegada como atraso."
    )
    is_mandatory = fields.Boolean(
        string='Parada Obligatoria',
        default=True
    )
    stop_direction = fields.Selection([
        ('outbound', 'Ida / Salida'),
        ('inbound', 'Retorno / Regreso'),
        ('both', 'Ambos Sentidos')
    ], string='Sentido Parada', default='outbound', required=True)

