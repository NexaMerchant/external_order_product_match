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
            summary_html = ''
            for line in order.external_order_line_ids.sudo():
                # 图片URL，假设 'images_binary' 是 external.order.line 模型中存储图片二进制数据的字段名
                img_url = f'/web/image/external.order.line/{line.id}/images_binary'
                
                external_sku = line.external_sku or ''
                external_name = line.external_name or ''
                price = line.price_unit or 0.0
                quantity = line.quantity or 0

                odoo_product_info_html = ''
                stock_status_html = '<div style="font-size:12px;color:#888;">Odoo库存: N/A</div>'

                if line.product_id:
                    product = line.product_id
                    odoo_product_sku = product.default_code or 'N/A'
                    odoo_product_name = product.name or ''
                    odoo_product_info_html = f'<div style="font-size:12px;color:#888;">Odoo商品: {odoo_product_name} (SKU: {odoo_product_sku})</div>'
                    
                    is_out_of_stock = product.qty_available < line.quantity
                    stock_status_text = '<span style="color:red;">缺货</span>' if is_out_of_stock else '<span style="color:green;">有货</span>'
                    stock_status_html = f'<div style="font-size:12px;">Odoo库存: {stock_status_text} (可用: {product.qty_available:.0f})</div>'
                else:
                    odoo_product_info_html = '<div style="font-size:12px;color:#888;">Odoo商品: 未配对</div>'

                match_status_icon = "✅ 已配对" if line.confirmed else "❌ 未配对"
                match_link_html = ''
                if not line.confirmed:
                    match_link_html = (
                        f'<button type="button" class="btn btn-link btn-sm match-btn" '
                        f'data-order-id="{order.id}" data-external-order-line-id="{line.id}" '
                        f'style="color:blue;text-decoration:underline;padding:0;font-size:12px;margin-left:5px;">配对</button>'
                    )

                summary_html += '<table style="width:100%; border-collapse: collapse; margin-bottom: 5px; border: 1px solid #ddd;">'
                summary_html += '<tr>'
                
                # Image cell
                summary_html += '<td style="width: 70px; padding: 5px; vertical-align: top; text-align: center;">'
                summary_html += f'<img src="{img_url}" style="height:60px;width:60px;border:1px solid #ccc;" alt="商品图片"/>'
                summary_html += '</td>'
                
                # Details cell
                summary_html += '<td style="padding: 5px; vertical-align: top;">'
                #summary_html += f'<div style="font-size:13px;color:#333;font-weight:bold;">外部商品名: {external_name}</div>'
                summary_html += f'<div style="font-size:12px;color:#888;">外部SKU: {external_sku}</div>'
                summary_html += f'<div style="font-size:12px;color:#888;">价格: {price:.2f} / 数量: {quantity:.0f}</div>'
                summary_html += odoo_product_info_html
                summary_html += stock_status_html
                summary_html += f'<div style="font-size:12px;">配对状态: {match_status_icon}{match_link_html}</div>'
                summary_html += '</td>'
                
                summary_html += '</tr>'
                summary_html += '</table>'
            
            order.external_order_line_summary = summary_html

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
