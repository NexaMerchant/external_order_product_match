from odoo import models, fields, api
import base64
from odoo.http import request
import io
import xlsxwriter

class SaleOrderPurchaseReport(models.TransientModel):
    _name = 'sale.order.purchase.report'
    _description = '销售订单采购需求报表'

    start_date = fields.Date(string='开始日期', required=True)
    end_date = fields.Date(string='结束日期', required=True)
    group_by = fields.Selection([
        ('day', '按天'),
        ('week', '按周'),
        ('month', '按月')
    ], string='分组方式', default='day')

    results_ids = fields.One2many('sale.order.purchase.report.line', 'report_id', string='统计结果')

    def export_to_excel(self):
        # 这里生成Excel文件内容，返回下载动作
        # 假设你已生成 base64 编码的文件内容 file_content
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('采购需求报表')

        # 写表头
        headers = ['时间分组', '产品', '总数量', '订单数', 'SKU', '在手数量', '需要采购数量']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        # 写数据
        for row, line in enumerate(self.results_ids, start=1):
            worksheet.write(row, 0, line.date_key)
            worksheet.write(row, 1, line.product_id.display_name or '')
            worksheet.write(row, 2, line.qty_total)
            worksheet.write(row, 3, line.order_count)
            worksheet.write(row, 4, line.product_sku or '')
            worksheet.write(row, 5, line.on_hand_qty)
            worksheet.write(row, 6, line.purchase_qty)

        workbook.close()
        output.seek(0)
        file_content = output.read()
        attachment = self.env['ir.attachment'].create({
            'name': '采购需求报表.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        download_url = '/web/content/%s?download=true' % attachment.id
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'self',
        }
       

    def action_generate_report(self):
        self.ensure_one()

        SaleOrderLine = self.env['sale.order.line']
        domain = [('order_id.state', 'in', ['sale', 'done']),
                  ('order_id.date_order', '>=', self.start_date),
                  ('order_id.date_order', '<=', self.end_date)]

        lines = SaleOrderLine.search(domain)
        grouped = {}

        for line in lines:
            key_date = line.order_id.date_order.date()
            if self.group_by == 'week':
                key_date = line.order_id.date_order.strftime('%Y-W%W')
            elif self.group_by == 'month':
                key_date = line.order_id.date_order.strftime('%Y-%m')

            key = (key_date, line.product_id.id)

            if key not in grouped:
                grouped[key] = {
                    'product_id': line.product_id.id,
                    'qty_total': 0,
                    'date_key': key_date,
                    'order_count': 0,
                }

            grouped[key]['qty_total'] += line.product_uom_qty
            grouped[key]['order_count'] += 1

        self.results_ids.unlink()

        for data in grouped.values():
            self.env['sale.order.purchase.report.line'].create({
                'report_id': self.id,
                'product_id': data['product_id'],
                'product_sku': self.env['product.product'].browse(data['product_id']).default_code,
                'on_hand_qty': self.env['product.product'].browse(data['product_id']).qty_available,
                'purchase_qty': data['qty_total'] - self.env['product.product'].browse(data['product_id']).qty_available,
                'qty_total': data['qty_total'],
                'order_count': data['order_count'],
                'date_key': data['date_key'],
            })

        self.results_ids = [(6, 0, [line.id for line in self.results_ids])]

class SaleOrderPurchaseReportLine(models.TransientModel):
    _name = 'sale.order.purchase.report.line'
    _description = '销售订单采购需求报表行'

    report_id = fields.Many2one('sale.order.purchase.report', string='报表')
    product_id = fields.Many2one('product.product', string='产品')
    # 商品SKU
    product_sku = fields.Char(string='SKU', related='product_id.default_code')
    qty_total = fields.Float(string='总数量')
    order_count = fields.Integer(string='订单数')
    # 在手数量
    on_hand_qty = fields.Float(string='在手数量', compute='_compute_on_hand_qty', store=True)
    # 需要采购数量
    purchase_qty = fields.Float(string='需要采购数量', compute='_compute_purchase_qty', store=True)
    date_key = fields.Char(string='时间分组')

    def _compute_on_hand_qty(self):
        for line in self:
            # 这里假设有 product_id 字段
            if line.product_id:
                line.on_hand_qty = line.product_id.qty_available
            else:
                line.on_hand_qty = 0.0

    def _compute_purchase_qty(self):
        for line in self:
            # 需要采购数量 = 总数量 - 在手数量
            line.purchase_qty = (line.qty_total or 0.0) - (line.on_hand_qty or 0.0)
