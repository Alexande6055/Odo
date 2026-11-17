# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class TransportDashboard(models.Model):
    _name = 'transport.dashboard'
    _description = 'Centro de Control y Monitoreo de Transporte Universitario'

    name = fields.Char(
        string='Panel de Control',
        default='Centro de Mando y Calidad de Transporte'
    )
    dashboard_html = fields.Html(
        string='Dashboard',
        compute='_compute_dashboard_html',
        sanitize=False
    )

    def _compute_dashboard_html(self):
        for record in self:
            record.dashboard_html = '''
                <div class="o_transport_dashboard_wrapper" style="width: 100%; min-height: 86vh; border: none; overflow: hidden; background: #0f172a; margin: -16px;">
                    <iframe src="/transport/dashboard?embedded=1" 
                            style="width: 100%; height: calc(100vh - 100px); border: none; display: block;" 
                            allow="geolocation">
                    </iframe>
                </div>
            '''

    def action_open_fullscreen(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/transport/dashboard',
            'target': 'new',
        }
