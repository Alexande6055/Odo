# -*- coding: utf-8 -*-
from odoo import models, fields

class TransportDashboard(models.Model):
    _name = 'transport.dashboard'
    _description = 'Centro de Control y Monitoreo de Transporte Universitario'

    name = fields.Char(string='Nombre', default='Centro de Mando UTA')
