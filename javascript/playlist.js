$(document).ready(function() {
    let params = new URLSearchParams(location.search);
    let url_id = params.get('id');
    let url_language = params.get('language');

    var loadingScreen = pleaseWait({
         logo: "",
         backgroundColor: '#722BD3',
         loadingHtml: '<img src="../images/boombox.png" id="boombox-loading" draggable="false" /><h3>Creating customized playlist...</h3><div class="spinner"><div class="rect1"></div><div class="rect2"></div><div class="rect3"></div><div class="rect4"></div><div class="rect5"></div></div>'
   });
    const url = 'http://localhost:8080/start-analysis?playlist=' + url_id + '&language=' + url_language;
    $.ajax({
        url: url,
        type: 'POST',
        success: function(results) {
            let results_json = JSON.parse(results);
            let tracks = results_json['tracks'];
            console.log(tracks);

            for (let i = 0; i < tracks.length; i++) {
                let track = tracks[i];

                let title = track['name'];
                let artist = track['artists'][0]['name'];
                let id = track['id'];
                let duration_ms = track['duration_ms'];
                duration_ms = parseInt(duration_ms);

                let duration_m = Math.floor((duration_ms / 1000) / 60);
                let duration_s = forceTwoDigits(Math.floor((duration_ms / 1000) % 60));

                $('.result-playlist-body').append('<div class="result-playlist-track"><span id="result-track-title">' + title +
                    '</span><span id="result-track-artist">' + artist +
                    '</span><span id="result-track-length">' + duration_m + ':' + duration_s +
                    '</span></div>');
            }

            loadingScreen.finish();
        },
        error: function(error) {
            // TODO: FIX
            console.log('Error' + error);
            loadingScreen.updateLoadingHtml('<h3>Oops! Something went wrong.</h3>');
            loadingScreen.finish();
        }
    });
});

function forceTwoDigits(n) {
  return ('0' + n).slice(-2);
}