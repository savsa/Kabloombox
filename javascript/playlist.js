$(document).ready(function() {
    let params = new URLSearchParams(location.search);
    let url_id = params.get('id');
    let url_language = params.get('language');
    let tracks = [];
    let track_uris = [];

    var loadingScreen = pleaseWait({
         logo: "",
         backgroundColor: '#722BD3',
         loadingHtml: '<img src="../images/boombox.png" id="boombox-loading" draggable="false" /><h3>Creating customized playlist...</h3><div class="spinner"><div class="rect1"></div><div class="rect2"></div><div class="rect3"></div><div class="rect4"></div><div class="rect5"></div></div>'
   });
    // TODO: send the access token to the post request intstead of getting it through the cookie?
    const url = 'http://localhost:8080/start-analysis?playlist=' + url_id + '&language=' + url_language;
    $.ajax({
        url: url,
        type: 'POST',
        success: function(results) {
            let results_json = JSON.parse(results);
            tracks = results_json['tracks'];
            console.log(tracks);

            for (let i = 0; i < tracks.length; i++) {
                let track = tracks[i];

                let title = track['name'];
                let artist = track['artists'][0]['name'];
                let id = track['id'];
                let duration_ms = track['duration_ms'];
                let uri = track['uri'];
                duration_ms = parseInt(duration_ms);

                let duration_m = Math.floor((duration_ms / 1000) / 60);
                let duration_s = forceTwoDigits(Math.floor((duration_ms / 1000) % 60));

                let $track = $('<div class="result-playlist-track"><span id="result-track-title">' + title +
                    '</span><span id="result-track-artist">' + artist +
                    '</span><span id="result-track-length">' + duration_m + ':' + duration_s +
                    '</span></div>');
                $track.data('uri', uri);
                $('.result-playlist-body').append($track);

                track_uris.push(uri);
            }

            loadingScreen.finish();
        },
        error: function(error) {
            // TODO: FIX
            loadingScreen.finish();
            // window.location.href = '/';
        }
    });


    // $('body').delegate('.result-playlist-track','click',function() {
    //     console.log('blah');
    //     // alert(1);
    //     $.post('http://localhost:8080/play?uri=' + $('.result-playlist-track').data('uri'));
    // });

    $('body').on('click', '.result-playlist-track', function() {
        console.log('blah');
        alert(1);
        $.post('http://localhost:8080/play?uri=' + $('.result-playlist-track').data('uri'));
    });




    /*Dropdown Menu*/
    $('.dropdown').click(function () {
        $(this).attr('tabindex', 1).focus();
        $(this).toggleClass('active');
        $(this).find('.dropdown-menu').slideToggle(300);
        // $('#arrow').rotate({ endDeg:180, persist:true });

        $('#arrow').animate({ deg: 180 }, {
            duration: 70,
            step: function(now) {
                $(this).css({ transform: 'rotate(' + now + 'deg)' });
            }
        });


    });

    $('.dropdown').focusout(function () {
        $('.dropdown').removeClass('active');
        $('.dropdown').find('.dropdown-menu').slideUp(300);

        $('#arrow').animate({ deg: 360 }, {
            duration: 70,
            step: function(now) {
                $(this).css({ transform: 'rotate(' + now + 'deg)' });
            }
        });
    });


    $('.result-playlist-add-button').click(function () {
        $.post('/create', function() {
            location.reload(true);
        });
    });




});




function forceTwoDigits(n) {
  return ('0' + n).slice(-2);
}