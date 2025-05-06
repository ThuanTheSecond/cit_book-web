(function($) {
    'use strict';
    
    // Hàm xử lý khi select thay đổi
    function handleTopicSelect(select) {
        const row = select.closest('tr');
        
        // Nếu là empty-form, chuyển đổi thành form-row bình thường
        if (row.classList.contains('empty-form')) {
            row.classList.remove('empty-form');
            row.classList.add('form-row');
            row.classList.add('dynamic-book_topics');
            
            // Cập nhật ID của row
            const newId = 'book_topics-' + (document.querySelectorAll('tr.form-row.dynamic-book_topics').length - 1);
            row.id = newId;
            
            // Cập nhật các input/select trong row
            row.querySelectorAll('input, select').forEach(input => {
                const oldName = input.name;
                const oldId = input.id;
                input.name = oldName.replace('__prefix__', newId.split('-')[1]);
                input.id = oldId.replace('__prefix__', newId.split('-')[1]);
            });
        }

        const titleCell = row.querySelector('td.original');
        if (select.value && titleCell) {
            const selectedOption = select.options[select.selectedIndex];
            titleCell.textContent = selectedOption.text;
            
            // Thêm nút Remove nếu chưa có
            const deleteCell = row.querySelector('td.delete');
            if (deleteCell && !deleteCell.querySelector('.remove-btn')) {
                const removeBtn = document.createElement('a');
                removeBtn.textContent = 'Remove';
                removeBtn.className = 'remove-btn btn-danger';
                removeBtn.href = '#';
                removeBtn.style.marginLeft = '5px';
                removeBtn.style.color = 'white';
                removeBtn.style.backgroundColor = '#dc3545';
                removeBtn.style.padding = '2px 8px';
                removeBtn.style.borderRadius = '3px';
                removeBtn.style.textDecoration = 'none';
                removeBtn.onclick = function(e) {
                    e.preventDefault();
                    if (confirm('Bạn có chắc chắn muốn xóa chủ đề này?')) {
                        // Đánh dấu form để xóa
                        const deleteInput = row.querySelector('input[name$="-DELETE"]');
                        if (deleteInput) {
                            deleteInput.checked = true;
                        }
                        // Ẩn row
                        row.style.display = 'none';
                        updateFormIndexes();
                    }
                };
                deleteCell.appendChild(removeBtn);
            }
        }
    }

    // Hàm cập nhật index cho các form
    function updateFormIndexes() {
        const rows = document.querySelectorAll('tr.form-row.dynamic-book_topics');
        rows.forEach((row, index) => {
            row.id = `book_topics-${index}`;
            row.querySelectorAll('input, select').forEach(input => {
                input.name = input.name.replace(/\d+/, index);
                input.id = input.id.replace(/\d+/, index);
            });
        });
        
        // Cập nhật TOTAL_FORMS
        const totalForms = document.querySelector('#id_book_topics-TOTAL_FORMS');
        if (totalForms) {
            totalForms.value = rows.length;
        }
    }

    // Khởi tạo các select fields
    function initializeTopicSelects() {
        document.querySelectorAll('select[id*="topic_id"]').forEach(select => {
            // Xóa event listener cũ nếu có
            const newSelect = select.cloneNode(true);
            select.parentNode.replaceChild(newSelect, select);
            
            // Thêm event listener mới
            newSelect.addEventListener('change', () => handleTopicSelect(newSelect));
            
            // Xử lý các select đã có giá trị
            if (newSelect.value) {
                handleTopicSelect(newSelect);
            }
        });
    }

    // Khởi tạo khi trang được load
    document.addEventListener('DOMContentLoaded', function() {
        initializeTopicSelects();
        
        // Xử lý khi thêm hàng mới
        const addButton = document.querySelector('.add-row a');
        if (addButton) {
            addButton.addEventListener('click', function(e) {
                e.preventDefault();
                // Đợi một chút để DOM được cập nhật
                setTimeout(() => {
                    initializeTopicSelects();
                }, 100);
            });
        }
    });

})(django.jQuery);
