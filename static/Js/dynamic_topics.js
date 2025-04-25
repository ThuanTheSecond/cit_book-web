(function($) {
    'use strict';
    
    // Hàm để refresh các select fields của topic
    function updateTopicSelects(win, newId, newRepr) {
        // Tìm tất cả các select fields của topic trong inline formsets
        const topicSelects = document.querySelectorAll('select[id$="-topic_id"]');
        
        topicSelects.forEach(select => {
            // Thêm option mới vào mỗi select
            const option = new Option(newRepr, newId);
            select.add(option);
            
            // Sắp xếp lại các options theo alphabet
            const options = Array.from(select.options);
            options.sort((a, b) => a.text.localeCompare(b.text));
            
            select.innerHTML = '';
            options.forEach(item => select.add(item));
        });
    }

    // Override hàm dismissAddRelatedObjectPopup mặc định của Django
    window.dismissAddRelatedObjectPopup = function(win, newId, newRepr) {
        const name = windowname_to_id(win.name);
        const elem = document.getElementById(name);
        
        if (elem) {
            if (elem.nodeName === 'SELECT') {
                elem.options[elem.options.length] = new Option(newRepr, newId, true, true);
                // Cập nhật tất cả các topic selects khác
                updateTopicSelects(win, newId, newRepr);
            } else {
                const href = document.getElementById(name + '_link');
                if (href) {
                    href.innerHTML = newRepr;
                    href.href = href.href.replace(/(.*\/)(\d+)(\/)$/, '$1' + newId + '$3');
                }
            }
        }
        // Đóng window và xóa reference
        if (win && !win.closed) {
            win.close();
        }
    };

    // Override hàm showAddAnotherPopup mặc định của Django
    window.showAddAnotherPopup = function(triggeringLink) {
        const name = triggeringLink.id.replace(/^add_/, '');
        const href = triggeringLink.href;
        const win = window.open(href, name, 'height=500,width=800,resizable=yes,scrollbars=yes');
        win.focus();
        return false;
    };
})(django.jQuery);
