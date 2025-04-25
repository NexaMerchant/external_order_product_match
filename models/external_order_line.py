from odoo import models, fields, api
from odoo.exceptions import UserError

class ExternalOrderLine(models.Model):
    _name = 'external.order.line'
    _description = 'External Order Line (待确认 SKU)'

    sale_order_id = fields.Many2one('sale.order', string='销售订单', required=True, ondelete='cascade')
    external_sku = fields.Char('外部 SKU', required=True)
    external_name = fields.Char('外部商品名')
    quantity = fields.Float('数量')
    price_unit = fields.Float('单价')
    images = fields.Text('图片')
    product_type = fields.Char('商品类型')

    product_id = fields.Many2one('product.product', string='匹配商品')
    confirmed = fields.Boolean('已确认', default=False)

    def action_confirm_product(self):
        for line in self:
            if not line.product_id:
                raise UserError("请先选择匹配商品")
            so_line = self.env['sale.order.line'].search([
                ('order_id', '=', line.sale_order_id.id),
                ('product_id.default_code', '=', 'PLACEHOLDER'),
                ('name', 'ilike', line.external_sku),
            ], limit=1)
            if so_line:
                so_line.product_id = line.product_id
                so_line.name = line.product_id.display_name
                line.confirmed = True

            # 写入映射表
            mapping_model = self.env['external.sku.mapping']
            existing = mapping_model.search([('external_sku', '=', line.external_sku)], limit=1)
            if not existing:
                mapping_model.create({
                    'external_sku': line.external_sku,
                    'product_id': line.product_id.id
                })

class ExternalSkuMapping(models.Model):
    _name = 'external.sku.mapping'
    _description = 'SKU 映射表'

    external_sku = fields.Char('外部 SKU', required=True)
    product_id = fields.Many2one('product.product', string='内部商品', required=True)

    _sql_constraints = [
        ('external_sku_unique', 'unique(external_sku)', '每个 SKU 只能映射一个商品')
    ]
