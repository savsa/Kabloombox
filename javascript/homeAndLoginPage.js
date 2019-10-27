$(document).ready(function() {
    $('#logout').click(function() {
        $.post('http://localhost:8080/logout', function() {
            location.reload(true);
        });
    });
});