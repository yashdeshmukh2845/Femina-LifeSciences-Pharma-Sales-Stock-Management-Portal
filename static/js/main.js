// Custom JS for Pharma Portal
$(document).ready(function() {
    // Sidebar Toggler
    $('#sidebarCollapse').on('click', function() {
        $('#sidebar').toggleClass('active');
    });

    // Auto-dismiss flashes
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
});
