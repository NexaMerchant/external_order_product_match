{
    'name': 'External Order Product Match',
    'version': '1.0',
    'summary': 'Handle unmatched SKU in external orders with manual mapping and auto learning',
    'category': 'Sales',
    'depends': ['sale', 'stock', 'product','purchase'],
    'author': 'Steve Liu',
    'website': 'https://github.com/NexaMerchant/external_order_product_match',
    'description': """
        This module provides a mechanism to handle unmatched SKU in external orders. 
        It allows for manual mapping of products and auto learning from past mappings.
    """,
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/external_order_line_views.xml',
        'views/sale_order_views.xml',
        'views/match_product_template.xml',
        'views/sale_order_purchase_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'external_order_product_match/static/src/js/external_order_match.js',
        ],
    }, 
    'installable': True,
}
