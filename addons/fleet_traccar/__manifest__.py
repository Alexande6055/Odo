# -*- coding: utf-8 -*-
{
    'name': 'Fleet Traccar GPS Integration',
    'version': '16.0.1.0.0',
    'summary': 'Conecta vehículos de Fleet con Traccar GPS Server',
    'description': """
Módulo de integración entre Odoo Fleet y servidor Traccar GPS.
Permite vincular vehículos por su IMEI, registrar dispositivos en Traccar y sincronizar coordenadas en tiempo real.
    """,
    'category': 'Human Resources/Fleet',
    'author': 'Alexander',
    'depends': ['fleet'],
    'data': [
        'views/fleet_vehicle_views.xml',
        'views/res_config_settings_views.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
