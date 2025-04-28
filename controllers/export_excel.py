from odoo import http
from odoo.http import request
import io
import xlsxwriter

class SaleOrderPurchaseReportController(http.Controller):

    @http.route('/sale_order_purchase_report/download_excel', type='http', auth='user')
    def download_excel(self, **kwargs):
        report_id = kwargs.get('report_id')
        if not report_id:
            return request.not_found()

        report = request.env['sale.order.purchase.report'].browse(int(report_id))
        if not report.exists():
            return request.not_found()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('采购需求')

        # 表头
        headers = ['时间分组', '产品', '总数量', '订单数']
        for col_num, header in enumerate(headers):
            sheet.write(0, col_num, header)

        # 内容
        row = 1
        for line in report.results_ids:
            sheet.write(row, 0, line.date_key)
            sheet.write(row, 1, line.product_id.display_name)
            sheet.write(row, 2, line.qty_total)
            sheet.write(row, 3, line.order_count)
            row += 1

        workbook.close()
        output.seek(0)

        # 返回下载
        return request.make_response(output.read(), [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', 'attachment; filename=采购需求报表.xlsx')
        ])
