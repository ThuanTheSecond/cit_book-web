(function($) {
    'use strict';
    
    $(document).ready(function() {
        // Khởi tạo Select2
        $('.select2-topics').select2({
            theme: "classic",
            width: 'resolve',
            placeholder: "Chọn chủ đề...",
            allowClear: true,
            ajax: {
                delay: 250,
                url: '/admin/home/topic/autocomplete/',
                data: function(params) {
                    return {
                        term: params.term || '',
                        page: params.page || 1
                    };
                }
            }
        });

        // Xử lý thêm topic mới
        $(document).on('click', '.add-another', function(e) {
            e.preventDefault();
            var href = this.href;
            var name = this.getAttribute('id').replace(/^add_/, '');
            var win = window.open(href, name, 'height=500,width=800,resizable=yes,scrollbars=yes');
            win.focus();
            return false;
        });

        // Xử lý sau khi thêm topic mới
        window.dismissAddRelatedObjectPopup = function(win, newId, newRepr) {
            var $select = $('.select2-topics');
            
            // Thêm option mới
            var newOption = new Option(newRepr, newId, true, true);
            $select.append(newOption).trigger('change');
            
            win.close();
        };
    });
})(django.jQuery);