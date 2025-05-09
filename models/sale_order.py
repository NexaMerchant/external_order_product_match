from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    external_order_line_ids = fields.One2many(
        'external.order.line', 'sale_order_id', string='商品'
    )

    external_order_line_summary = fields.Html(
       compute="_compute_external_summary",
       string="外部商品汇总",
       sanitize=False,
    )

    @api.depends(
        'external_order_line_ids.confirmed',
        'external_order_line_ids.images',
        'external_order_line_ids.external_name',
        'external_order_line_ids.price_unit',
        'external_order_line_ids.external_sku',
        'external_order_line_ids.quantity',
        'external_order_line_ids.product_id'
    )
    def _compute_external_summary(self):
        for order in self:
            summary = []
            for line in order.external_order_line_ids.sudo():
                # 图片展示
                # img_html = ''
                img_url = f'/web/image/external.order.line/{line.id}/images_binary'
                # img_html = f'<img src="data:image/png;base64,{line.images.decode() if isinstance(line.images, bytes) else line.images}" style="height:80px;width:80px;vertical-align:middle;"/>'
                img_html = (
                    f'<img src="{img_url}" '
                    f'style="height:80px;width:80px;vertical-align:middle;"/>'
                )
                # 商品名、SKU、数量、价格、状态
                status = "✅" if line.confirmed else "❌"
                name = line.external_name or ''
                sku = line.external_sku or ''
                qty = line.quantity or 0
                price = line.price_unit or 0
                product = line.product_id.default_code if line.product_id else ''
                stock_qty = line.product_id.qty_available if line.product_id else 0
                match_link = ''
                if not line.confirmed:
                    match_link = (
                        f'<button type="button" class="btn btn-link btn-sm match-btn" '
                        f'data-order-id="{order.id}" data-external-order-line-id="{line.id}" '
                        f'style="color:blue;text-decoration:underline;padding:0;">配对</button>'
                    )
                summary.append(
                    f'<div style="margin-bottom:2px;">'
                    f'{img_html}'
                    f'<span style="color:#888;">SKU: {sku}<br/>'
                    f'数量: {qty} <br/>'
                    f'价格：{price:.2f}<br/>'
                    f'配对: {product} <br/>'
                    f'库存: {stock_qty}</span> '
                    f'{status}'
                    # add matching link
                    f'{match_link}'
                    f'</div>'
                )
            order.external_order_line_summary = ''.join(summary)

    def action_open_unmatched_lines(self):
        return {
            'type': 'ir.actions.act_window',
            'name': '待确认商品',
            'res_model': 'external.order.line',
            'view_mode': 'tree,form',
            'domain': [('sale_order_id', '=', self.id), ('confirmed', '=', False)],
            'context': {'default_sale_order_id': self.id},
        }
    
    def action_open_match_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': '外部商品配对',
            'res_model': 'external.order.line.match.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
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
                'images': item.get('images', False),
                'product_type': item.get('product_type', False),
                'product_url': item.get('product_url', False),
                'product_id': product_id,
                'confirmed': confirmed,
            })

        return order
