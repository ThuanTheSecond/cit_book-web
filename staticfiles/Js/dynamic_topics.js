(function ($) {
  "use strict";

  // Function to handle topic selection changes
  function handleTopicSelect(select) {
    const $select = $(select);
    const $row = $select.closest("tr");

    // Update the display when a topic is selected
    if ($select.val()) {
      const selectedText = $select.find("option:selected").text();

      // Find or create a display cell for the topic name
      let $displayCell = $row.find(".topic-display");
      if ($displayCell.length === 0) {
        // Create display cell if it doesn't exist
        $displayCell = $('<td class="topic-display"></td>');
        $select.closest("td").after($displayCell);
      }

      $displayCell.text(selectedText);

      // Show the row if it was hidden
      $row.show();

      // Remove empty-form class if present
      $row.removeClass("empty-form");
    } else {
      // If no topic selected, hide display
      $row.find(".topic-display").text("");
    }

    // Prevent duplicate topic selections
    validateTopicSelections();
  }

  // Function to prevent duplicate topic selections
  function validateTopicSelections() {
    const selectedValues = [];
    const $allSelects = $('select[name*="topic_id"]');

    $allSelects.each(function () {
      const $select = $(this);
      const value = $select.val();
      const $row = $select.closest("tr");

      // Skip if row is marked for deletion
      if ($row.find('input[name*="DELETE"]').is(":checked")) {
        return;
      }

      if (value) {
        if (selectedValues.includes(value)) {
          // Duplicate found - clear this selection
          $select.val("");
          $select.closest("tr").find(".topic-display").text("");
          alert("Chủ đề này đã được chọn. Vui lòng chọn chủ đề khác.");
        } else {
          selectedValues.push(value);
        }
      }
    });
  }

  // Function to initialize topic selects
  function initializeTopicSelects() {
    // Remove existing event listeners to prevent duplicates
    $('select[name*="topic_id"]').off("change.topicSelect");

    // Add event listeners
    $('select[name*="topic_id"]').on("change.topicSelect", function () {
      handleTopicSelect(this);
    });

    // Initialize existing selections
    $('select[name*="topic_id"]').each(function () {
      if (this.value) {
        handleTopicSelect(this);
      }
    });
  }

  // Function to handle when new inline forms are added
  function onFormsetAdd() {
    // Reinitialize selects when new forms are added
    setTimeout(initializeTopicSelects, 100);
  }

  // Initialize when DOM is ready
  $(document).ready(function () {
    console.log("Dynamic topics JS loaded");

    // Initial setup
    initializeTopicSelects();

    // Handle Django's add another button
    $(document).on("click", ".add-row a", function () {
      setTimeout(initializeTopicSelects, 200);
    });

    // Handle delete button clicks - use Django's existing functionality
    $(document).on("change", 'input[name*="DELETE"]', function () {
      const $checkbox = $(this);
      const $row = $checkbox.closest("tr");

      if ($checkbox.is(":checked")) {
        // Row is marked for deletion - hide it
        $row.addClass("deleted-row").fadeOut();
      } else {
        // Row is unmarked for deletion - show it
        $row.removeClass("deleted-row").fadeIn();
      }

      // Revalidate selections
      validateTopicSelections();
    });

    // Watch for formset changes (if using Django's formset JavaScript)
    if (typeof django !== "undefined" && django.jQuery) {
      django.jQuery(document).on("formset:added", onFormsetAdd);
    }
  });
})(django.jQuery || jQuery);
