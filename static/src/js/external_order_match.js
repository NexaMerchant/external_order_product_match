odoo.define('external_order_product_match.external_order_match', function (require) {
    "use strict";
    var core = require('web.core');

    $(document).on('click', '.match-btn', function(e){
        console.log('Match button clicked!');
        e.preventDefault();
        e.stopPropagation();
        var order_id = $(this).data('order-id');
        var external_order_line_id = $(this).data('external-order-line-id');
        // 你的配对逻辑...
        // redirect to the match page with order_id and external_order_line_id as parameters
        var url = '/match_product?order_id=' + order_id + '&external_order_line_id=' + external_order_line_id;
        window.location.href = url;
    });
});