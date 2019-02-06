$(document).ready(function() {
    const url = 'http://localhost:8080/start-analysis?playlist=' + $('.playlist-button').val();
    $('.playlist-button').click(function() {
        $.ajax({
            url: url,
            type: 'GET',
            success: function(result) {
                console.log(result)
            },
            error: function(error) {
                console.log('Error ${error}')
            }
        })
    })
})
