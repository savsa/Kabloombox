$(document).ready(function() {
    $('.playlist-button').click(function() {
        const url = 'http://localhost:8080/start-analysis?playlist=' + this.value + '&language=' + $('.language').val();
        $.ajax({
            url: url,
            type: 'POST',
            success: function(results) {
                results = results.substring(1)
                results = results.split(" ");
                var uniqueResults = [];
                $.each(results, function(i, el){
                    if($.inArray(el, uniqueResults) === -1) uniqueResults.push(el);
                });
                results = uniqueResults;
                results.forEach(function(result) {
                    result = result.substring(2, 24);
                    let link = 'https://open.spotify.com/track/' + result;
                    $('.matches').append('<li><a target="_blank" href=' + link + '>' + result + '</a></li>');
                });
            },
            error: function(error) {
                console.log('Error ${error}')
            }
        })
    })
})
