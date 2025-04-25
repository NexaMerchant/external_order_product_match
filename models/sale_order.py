from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    external_order_line_ids = fields.One2many(
        'external.order.line', 'sale_order_id', string='External Order Lines'
    )

    def action_open_unmatched_lines(self):
        return {
            'type': 'ir.actions.act_window',
            'name': '待确认商品',
            'res_model': 'external.order.line',
            'view_mode': 'tree,form',
            'domain': [('sale_order_id', '=', self.id), ('confirmed', '=', False)],
            'context': {'default_sale_order_id': self.id},
        }

    @api.constrains('order_line')
    def _check_unmatched_products(self):
        for order in self:
            unconfirmed = self.env['external.order.line'].search([
                ('sale_order_id', '=', order.id),
                ('confirmed', '=', False)
            ])
            if unconfirmed:
                raise UserError("当前订单包含未确认商品，无法发货。")

    def create_external_order(self, external_data):
        """
        示例：根据外部订单数据创建订单
        external_data = {
            'partner_id': 3,
            'external_lines': [{'sku': 'ABC123', 'name': '外部商品名', 'qty': 2, 'price': 99}]
        }
        """
        placeholder = self.env['product.product'].search([('default_code', '=', 'PLACEHOLDER')], limit=1)
        if not placeholder:
            raise UserError("未找到占位商品 'PLACEHOLDER'")

        lines = []
        for item in external_data['external_lines']:
            mapping = self.env['external.sku.mapping'].search([
                ('external_sku', '=', item['sku'])
            ], limit=1)

            if mapping:
                product = mapping.product_id
                confirmed = True
            else:
                product = placeholder
                confirmed = False

            lines.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': item['qty'],
                'price_unit': item['price'],
                'name': product.name if confirmed else f"【待确认】{item['name']} (SKU: {item['sku']})"
            }))

        order = self.create({
            'partner_id': external_data['partner_id'],
            'order_line': lines,
        })

        for item in external_data['external_lines']:
            product_id = self.env['external.sku.mapping'].search([('external_sku', '=', item['sku'])], limit=1).product_id.id or False
            confirmed = True if product_id else False

            self.env['external.order.line'].create({
                'sale_order_id': order.id,
                'external_sku': item['sku'],
                'external_name': item['name'],
                'quantity': item['qty'],
                'price_unit': item['price'],
                'product_id': product_id,
                'confirmed': confirmed,
            })

        return order
