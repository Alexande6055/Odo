# -*- coding: utf-8 -*-
{
    'name': 'Sistema de Transporte Universitario y Monitoreo Traccar GPS',
    'version': '16.0.2.0.0',
    'summary': 'Gestión de rutas universitarias, paradas, recorridos, detección de incidencias e integración GPS con Traccar',
    'description': """
Sistema Integral de Transporte y Monitoreo GPS para la Universidad Técnica de Ambato.
- Gestión de vehículos asociados a dispositivos GPS en Traccar.
- Administración de rutas, paradas y puntos de control georreferenciados.
- Asignación y programación de recorridos con control de tiempos programados vs. reales.
- Motor de detección automática de retrasos, omisión de paradas, desvíos de ruta y pérdida de señal GPS.
- Fichas técnicas y cálculo dinámico de 8 métricas de transporte y 4 métricas de calidad de software (ISO/IEC 25010).
- Panel analítico y Dashboard en tiempo real.
    """,
    'category': 'Operations/Transportation',
    'author': 'Alexander - Gestión de Calidad de Software UTA',
    'depends': ['base', 'fleet'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/transport_demo_data.xml',
        'views/transport_route_views.xml',
        'views/transport_trip_views.xml',
        'views/transport_incident_views.xml',
        'views/transport_metrics_views.xml',
        'views/fleet_vehicle_views.xml',
        'views/res_config_settings_views.xml',
        'views/transport_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fleet_traccar/static/src/scss/odoo_header_custom.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
