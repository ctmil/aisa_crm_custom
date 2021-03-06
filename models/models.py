# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if res.opportunity_id:
            opportunity_id = res.opportunity_id
            opportunity_id._compute_expected_revenue()
        return res



    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        for rec in self:
            if rec.opportunity_id:
                opportunity_id = rec.opportunity_id
                opportunity_id._compute_expected_revenue()
        return res

class Lead(models.Model):
    _inherit = "crm.lead"

    def _compute_expected_revenue(self):
        for rec in self:
            res = 0
            domain = [('opportunity_id','=',rec.id)]
            orders = self.env['sale.order'].sudo().search(domain)
            for order in orders.filtered(lambda o: o.state != 'cancel'):
                res = res + order.amount_total
            rec.write({'expected_revenue': res})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('website'):
                vals['website'] = self.env['res.partner']._clean_website(vals['website'])
        leads = super(Lead, self).create(vals_list)

        for lead, values in zip(leads, vals_list):
            if any(field in ['active', 'stage_id'] for field in values):
                lead._handle_won_lost(values)
            if lead.phone or lead.mobile:
                if vals.get('phone') and vals.get('mobile'):
                    domain = [('phone','=',vals.get('phone')),('mobile','=',vals.get('mobile'))]
                elif vals.get('phone'):
                    domain = [('phone','=',vals.get('phone'))]
                elif vals.get('mobile'):
                    domain = [('mobile','=',vals.get('mobile'))]
                partner_id = self.env['res.partner'].search(domain,limit=1)
                if partner_id:
                    lead.partner_id = partner_id.id
                else:
                    lead.name = 'Contacto desconocido'

        return leads

    def write(self, vals):
        if vals.get('website'):
            vals['website'] = self.env['res.partner']._clean_website(vals['website'])

        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            stage_id = self.env['crm.stage'].browse(vals['stage_id'])
            if stage_id.is_won:
                vals.update({'probability': 100, 'automated_probability': 100})

        # stage change with new stage: update probability and date_closed
        if vals.get('probability', 0) >= 100 or not vals.get('active', True):
            vals['date_closed'] = fields.Datetime.now()
        elif vals.get('probability', 0) > 0:
            vals['date_closed'] = False

        if any(field in ['active', 'stage_id'] for field in vals):
            self._handle_won_lost(vals)

        if vals.get('phone') or vals.get('mobile'):
            if vals.get('phone') and vals.get('mobile'):
                domain = [('phone','=',vals.get('phone')),('mobile','=',vals.get('mobile'))]
            elif vals.get('phone'):
                domain = [('phone','=',vals.get('phone'))]
            elif vals.get('mobile'):
                domain = [('mobile','=',vals.get('mobile'))]
            partner_id = self.env['res.partner'].search(domain,limit=1)
            if partner_id:
                vals['partner_id'] = partner_id.id
            else:
                vals['name'] = 'Contacto desconocido'
        write_result = super(Lead, self).write(vals)

        return write_result

