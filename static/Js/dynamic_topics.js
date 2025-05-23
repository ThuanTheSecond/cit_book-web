(function ($) {
  "use strict";

  console.log("=== DYNAMIC TOPICS JS v7.0 LOADED ==="); // Debug line

  // Hàm xử lý khi select thay đổi
  function handleTopicSelect(select) {
    const row = select.closest("tr");
    console.log("=== HANDLE TOPIC SELECT CALLED ===", select.value); // Debug line

    // Hiển thị original của row này
    showOriginalDisplay(row);
    
    // Cập nhật nút delete cho row này
    updateDeleteButton(row);
  }

  // Hàm hiển thị original display cho row
  function showOriginalDisplay(row) {
    const select = row.querySelector('select[id*="topic_id"]');
    console.log("=== SHOW ORIGINAL DISPLAY CALLED ==="); // Debug line
    
    if (!select) {
      console.log("=== NO SELECT FOUND ===");
      return;
    }

    // Tìm td.original và p tag bên trong
    const originalCell = row.querySelector('td.original');
    if (!originalCell) {
      console.log("=== NO ORIGINAL CELL FOUND ===");
      return;
    }

    let displayP = originalCell.querySelector('p');
    if (!displayP) {
      console.log("=== NO P TAG IN ORIGINAL CELL, CREATING ONE ===");
      displayP = document.createElement('p');
      originalCell.appendChild(displayP);
    }

    // Hiển thị tên topic đã chọn trong thẻ p bên trong td.original
    if (select.value && select.value !== "") {
      const selectedOption = select.options[select.selectedIndex];
      if (selectedOption && selectedOption.text !== "---------") {
        displayP.textContent = selectedOption.text; // Chỉ hiển thị tên topic
        console.log("=== ORIGINAL DISPLAY UPDATED ===", selectedOption.text);
      } else {
        displayP.textContent = '';
        console.log("=== ORIGINAL DISPLAY HIDDEN (EMPTY SELECTION) ===");
      }
    } else {
      // Nếu không có topic được chọn, clear content
      displayP.textContent = '';
      console.log("=== ORIGINAL DISPLAY HIDDEN (NO VALUE) ===");
    }
  }

  // Hàm cập nhật nút delete dựa trên trạng thái của row
  function updateDeleteButton(row) {
    const select = row.querySelector('select[id*="topic_id"]');
    const deleteCell = row.querySelector("td.delete");

    if (!deleteCell) return;

    // Xóa tất cả nút cũ
    const existingBtns = deleteCell.querySelectorAll(".custom-delete-btn");
    existingBtns.forEach((btn) => btn.remove());

    // Ẩn Django's default delete checkbox và label
    const defaultCheckbox = deleteCell.querySelector('input[name$="-DELETE"]');
    const defaultLabel = deleteCell.querySelector("label");
    const inlineDeleteLink = deleteCell.querySelector(".inline-deletelink");
    
    if (defaultCheckbox) defaultCheckbox.style.display = "none";
    if (defaultLabel) defaultLabel.style.display = "none";
    if (inlineDeleteLink) inlineDeleteLink.style.display = "none";

    // Tạo nút delete mới
    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "custom-delete-btn";

    // CSS styling cho nút
    deleteBtn.style.padding = "6px 12px";
    deleteBtn.style.borderRadius = "4px";
    deleteBtn.style.border = "none";
    deleteBtn.style.cursor = "pointer";
    deleteBtn.style.fontSize = "12px";
    deleteBtn.style.fontWeight = "bold";
    deleteBtn.style.width = "100px";

    // Kiểm tra xem có topic được chọn không
    if (select && select.value && select.value !== "") {
      // Có topic được chọn
      deleteBtn.textContent = "Xóa thể loại";
      deleteBtn.style.backgroundColor = "#dc3545";
      deleteBtn.style.color = "white";

      deleteBtn.onclick = function (e) {
        e.preventDefault();
        e.stopPropagation();

        const selectedOption = select.options[select.selectedIndex];
        const topicName = selectedOption ? selectedOption.text : "thể loại này";

        if (confirm(`Bạn có chắc chắn muốn xóa "${topicName}"?`)) {
          // Đánh dấu form để xóa
          if (defaultCheckbox) {
            defaultCheckbox.checked = true;
          }

          // Ẩn row với hiệu ứng
          row.style.transition = "all 0.3s ease";
          row.style.opacity = "0.5";
          row.style.backgroundColor = "#ffebee";

          setTimeout(() => {
            row.style.display = "none";
          }, 300);
        }
      };
    } else {
      // Không có topic được chọn (row trống)
      deleteBtn.textContent = "Xóa trường";
      deleteBtn.style.backgroundColor = "#6c757d";
      deleteBtn.style.color = "white";

      deleteBtn.onclick = function (e) {
        e.preventDefault();
        e.stopPropagation();

        console.log("=== DELETING EMPTY ROW ==="); // Debug line

        // Xóa trực tiếp không cần confirm
        row.style.transition = "all 0.2s ease";
        row.style.opacity = "0";

        setTimeout(() => {
          row.remove();
          console.log("=== ROW REMOVED ==="); // Debug line
        }, 200);
      };
    }

    deleteCell.appendChild(deleteBtn);
  }

  // Khởi tạo các select fields và nút delete
  function initializeTopicSelects() {
    console.log("=== INITIALIZING TOPIC SELECTS ==="); // Debug line

    // Xử lý tất cả các select topic
    document.querySelectorAll('select[id*="topic_id"]').forEach((select) => {
      console.log("=== PROCESSING SELECT ===", select.id, select.value);
      
      // Khởi tạo nút delete cho row này
      const row = select.closest("tr");
      if (row) {
        // Hiển thị original cho các row đã có giá trị
        showOriginalDisplay(row);
        updateDeleteButton(row);
      }
    });

    // Ẩn Django's default elements
    hideDefaultDeleteElements();
  }

  // Hàm ẩn các element delete mặc định của Django
  function hideDefaultDeleteElements() {
    // Ẩn header "Delete?"
    const deleteHeader = document.querySelector(".inline-group .tabular th.delete");
    if (deleteHeader) {
      deleteHeader.style.display = "none";
    }

    // Ẩn tất cả checkbox, label và inline-deletelink
    document.querySelectorAll('input[name$="-DELETE"]').forEach((checkbox) => {
      checkbox.style.display = "none";
      const label = checkbox.nextElementSibling;
      if (label && label.tagName === "LABEL") {
        label.style.display = "none";
      }
    });

    // Ẩn tất cả Django's delete buttons
    document.querySelectorAll('.inline-deletelink').forEach((deleteLink) => {
      deleteLink.style.display = "none";
    });
  }

  // Khởi tạo khi DOM ready
  $(document).ready(function () {
    console.log("=== DOM READY ==="); // Debug line

    // Đợi một chút để DOM hoàn toàn ready
    setTimeout(() => {
      // Khởi tạo các select
      initializeTopicSelects();
    }, 500);

    // Theo dõi thay đổi trong select - sử dụng event delegation
    $(document).on("change", 'select[id*="topic_id"]', function () {
      console.log("=== SELECT CHANGED ===", this.value); // Debug line
      handleTopicSelect(this);
    });

    // Xử lý khi thêm row mới
    $(document).on('click', '.add-row a', function() {
      console.log("=== ADD ANOTHER CLICKED ===");
      
      setTimeout(() => {
        console.log("=== REINITIALIZING AFTER ADD ===");
        initializeTopicSelects();
      }, 300);
    });

    // CSS để style các element
    $("<style>")
      .prop("type", "text/css")
      .html(`
        .inline-group .tabular th.delete {
          display: none !important;
        }
        .inline-group .tabular input[name$="-DELETE"],
        .inline-group .tabular input[name$="-DELETE"] + label,
        .inline-group .tabular .inline-deletelink {
          display: none !important;
        }
        .inline-group .tabular td.delete {
          width: 120px !important;
          text-align: center !important;
        }
        .custom-delete-btn {
          transition: all 0.2s ease !important;
        }
        .custom-delete-btn:hover {
          opacity: 0.8 !important;
        }
        p.original {
          margin: 5px 0 !important;
          padding: 4px 8px !important;
          font-style: italic !important;
          color: #666 !important;
          font-size: 12px !important;
          background-color: #f8f9fa !important;
          border-left: 3px solid #007cba !important;
          border-radius: 3px !important;
          display: block !important;
        }
        p.original:empty {
          display: none !important;
        }
      `)
      .appendTo("head");
  });
})(django.jQuery || window.jQuery || window.$);
