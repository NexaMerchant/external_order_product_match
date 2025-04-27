from odoo import http
from odoo.http import request
import json


class MatchProductController(http.Controller):
    @http.route('/match_product', type='http', auth='user')
    def match_product(self, order_id=None, external_order_line_id=None, search='', **kwargs):
        # 获取订单和外部订单行
        order = request.env['sale.order'].sudo().browse(int(order_id))
        external_order_line = request.env['external.order.line'].sudo().browse(int(external_order_line_id))

        # 商品搜索
        domain = []
        if search:
            domain = ['|', ('default_code', 'ilike', search), ('name', 'ilike', search)]
        products = request.env['product.product'].sudo().search(domain, limit=20)

        return request.render('external_order_product_match.match_product_template', {
            'order': order,
            'external_order_line': external_order_line,
            'products': products,
            'search': search,
        })

    @http.route('/do_match_product', type='http', auth='user', method=['post'], csrf=False)
    def do_match_product(self, order_id=None, external_order_line_id=None, product_id=None, **kwargs):
        print("do_match_product")
        print("order_id:", order_id)
        print("product_id:", product_id)
        print("external_order_line_id:", external_order_line_id)
        order = request.env['sale.order'].sudo().browse(int(order_id))
        external_order_line = request.env['external.order.line'].sudo().browse(int(external_order_line_id))
        print("order_id:", order_id)
        print("external_order_line_id:", external_order_line_id)
        print("product_id:", product_id)
        if product_id:
            product = request.env['product.product'].sudo().browse(int(product_id))
            external_order_line.product_id = product.id
            external_order_line.confirmed = True

        # create or update the external_sku_mapping
        external_sku_mapping = request.env['external.sku.mapping'].sudo().search([
            ('external_sku', '=', external_order_line.external_sku),
        ], limit=1)
        if not external_sku_mapping:
            request.env['external.sku.mapping'].sudo().create({
                'product_id': external_order_line.product_id.id,
                'external_sku': external_order_line.external_sku,
            })
        else:
            external_sku_mapping.product_id = external_order_line.product_id.id

        # 更新订单行的产品
        for line in order.order_line:
            if line.product_id == external_order_line.product_id:
                line.product_id = external_order_line.product_id.id
                line.product_uom_qty = external_order_line.quantity
                line.price_unit = external_order_line.price_unit
                line.image_1920 = external_order_line.images
                line.name = external_order_line.external_name

        # if the order external_order_line allow to be confirmed, confirm the order

        if all(line.confirmed for line in order.order_line):
            order.action_confirm()

        # back to the order list view
        result = {'success': True, 'message': '配对成功', 'order_id': order.id}
        return request.make_response(
            json.dumps(result),
            headers=[('Content-Type', 'application/json')]
        )