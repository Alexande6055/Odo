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
        string='Punto de Origen',
        required=True,
        help="Lugar de partida (ej: Campus Huachi - Puerta Principal)"
    )
    destination = fields.Char(
        string='Punto de Destino',
        required=True,
        help="Lugar de llegada (ej: Campus Ingahurco - Edificio Central)"
    )
    estimated_distance = fields.Float(
        string='Distancia Estimada (km)',
        digits=(6, 2),
        default=0.0,
        help="Distancia programada del recorrido completo en kilómetros"
    )
    estimated_duration = fields.Float(
        string='Duración Estimada (min)',
        digits=(6, 1),
        default=30.0,
        help="Tiempo previsto de viaje en minutos"
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
        string='Coordenadas del Trazado Base',
        help="Pares de coordenadas lat,lon de la ruta para comprobación de desvíos."
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

    @api.depends('stop_ids', 'name')
    def _compute_route_map_html(self):
        import urllib.parse
        import json
        ICP = self.env['ir.config_parameter'].sudo()
        map_base = (ICP.get_param('fleet_traccar.map_url') or 'http://localhost:3000').strip().rstrip('/')
        user = (ICP.get_param('fleet_traccar.user') or '').strip()
        password = ICP.get_param('fleet_traccar.password') or ''

        for route in self:
            stops_data = []
            for s in route.stop_ids.sorted('sequence'):
                stops_data.append({
                    'name': s.name,
                    'seq': s.sequence,
                    'lat': s.latitude,
                    'lon': s.longitude,
                    'status': 'pending',
                    'schedTime': f"+{s.expected_offset_minutes}m",
                })
            query_params = {
                'compact': 'true',
                'routeName': route.name or '',
            }
            if user:
                query_params['user'] = user
            if password:
                query_params['pass'] = password
            if stops_data:
                query_params['stops'] = json.dumps(stops_data)

            map_url = f"{map_base}/?{urllib.parse.urlencode(query_params)}"
            full_url = map_url.replace('&compact=true', '').replace('?compact=true', '')
            route_title = route.name or 'Trazado Oficial de Ruta'

            route.route_map_html = f'''
                <div class="card shadow border-0 my-2 rounded-3 overflow-hidden">
                    <div class="card-header text-white d-flex justify-content-between align-items-center py-2 px-3" style="background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);">
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge rounded-pill bg-primary px-2 py-1">
                                <i class="fa fa-road me-1"></i>Ruta Oficial
                            </span>
                            <span class="fw-bold text-white small">{route_title}</span>
                        </div>
                        <a href="{full_url}" target="_blank" class="btn btn-sm btn-outline-info text-white">
                            <i class="fa fa-external-link me-1"></i>Pantalla Completa
                        </a>
                    </div>
                    <div class="card-body p-0 position-relative" style="height: 500px; background: #0f172a;">
                        <iframe src="{map_url}" 
                                style="width: 100%; height: 500px; border: none; display: block;" 
                                allow="geolocation">
                        </iframe>
                    </div>
                </div>
            '''

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

