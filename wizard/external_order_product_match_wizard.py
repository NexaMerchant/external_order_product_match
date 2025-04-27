from odoo import models, fields, api

class ExternalOrderLineMatchWizard(models.TransientModel):
    _name = 'external.order.line.match.wizard'
    _description = '外部商品配对'

    sale_order_id = fields.Many2one('sale.order', string='订单', required=True)
    line_ids = fields.One2many('external.order.line.match.wizard.line', 'wizard_id', string='外部商品')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        order_id = self.env.context.get('active_id')
        if order_id:
            res['sale_order_id'] = order_id
            lines = []
            for line in self.env['external.order.line'].search([('sale_order_id', '=', order_id)]):
                lines.append((0, 0, {
                    'external_line_id': line.id,
                    'external_name': line.external_name,
                    'external_sku': line.external_sku,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'images': line.images,
                    'product_id': line.product_id.id,
                    'confirmed': line.confirmed,
                }))
            res['line_ids'] = lines
        return res

    def action_confirm(self):
        for wizard_line in self.line_ids:
            line = wizard_line.external_line_id
            line.product_id = wizard_line.product_id
            line.confirmed = bool(wizard_line.product_id)
        return {'type': 'ir.actions.act_window_close'}

class ExternalOrderLineMatchWizardLine(models.TransientModel):
    _name = 'external.order.line.match.wizard.line'
    _description = '外部商品配对行'

    wizard_id = fields.Many2one('external.order.line.match.wizard', required=True, ondelete='cascade')
    external_line_id = fields.Many2one('external.order.line', string='外部商品', required=True)
    external_name = fields.Char('外部商品名')
    external_sku = fields.Char('外部SKU')
    quantity = fields.Integer('数量')
    price_unit = fields.Float('单价')
    images = fields.Binary('图片')
    product_id = fields.Many2one('product.product', string='Odoo商品')
    confirmed = fields.Boolean('已配对')