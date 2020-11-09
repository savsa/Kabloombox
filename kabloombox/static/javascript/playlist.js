// import Cookies from 'js.cookie.min.js'

$(document).ready(function () {
	// let link = new URL(window.location.search);
	// const urlParams = new URLSearchParams(link);
	// url_id = urlParams.get('id');
	// url_language = urlParamss.get('language');

	let params = new URLSearchParams(location.search);
	let url_id = params.get("id");
	let url_language = params.get("language");
	let track_uris = [];
	// let track_ids = [];
	let name = params.get("name");

	var loadingScreen = pleaseWait({
		logo: "",
		backgroundColor: "#722BD3",
		loadingHtml:
			'<img src="../static/images/boombox.png" id="boombox-loading" draggable="false" /><h3>Creating customized playlist...</h3><div class="spinner"><div class="rect1"></div><div class="rect2"></div><div class="rect3"></div><div class="rect4"></div><div class="rect5"></div></div>',
	});

	// TODO: send the access token to the post request intstead of getting it through the cookie?
	// const url = 'http://localhost:8080/start-analysis?playlist=' + url_id + '&language=' + url_language;
	console.log("name");
	console.log(name);
	$.ajax({
		url: "/api/start-analysis",
		type: "POST",
		dataType: "json",
		contentType: "application/json",
		data: JSON.stringify({
			playlist: url_id,
			language: url_language,
		}),
		success: function (response) {
			let data = JSON.parse(JSON.stringify(response));
			console.log(data);
			// data = data ? data : {};
			let tracks = data["tracks_info"];
			tracks = tracks ? tracks : {};
			let track_image_url = data["image_url"];
			if (track_image_url !== "") {
				$(".result-playlist-photo").attr("src", track_image_url);
			}

			console.log(tracks);

			for (let i = 0; i < Object.keys(tracks).length; i++) {
				let track = tracks[i];
				let title = track["name"];
				let artist = track["artists"];
				let id = track["id"];
				let duration_ms = track["duration_ms"];
				let uri = track["uri"];

				let preview_url = track["preview_url"];

				duration_ms = parseInt(duration_ms);
				// track_ids.push(id);

				let duration_m = Math.floor(duration_ms / 1000 / 60);
				let duration_s = forceTwoDigits(Math.floor((duration_ms / 1000) % 60));

				let $track;
				if (preview_url) {
					$track = $(`
<div class="result-playlist-track">
    <span class="result-track-title">${title}</span>
    <span class="result-track-artist">${artist}</span>
    <span class="result-track-length">${duration_m}:${duration_s}</span>
    <div class="play-container result-track-preview">
        <audio class="player" src="${preview_url}" preload="none" onended="on_playing_ended(this);"></audio>
        <div class="player-button play-icon"></div>
    </div>
</div>`);
				} else {
					$track = $(`
<div class="result-playlist-track">
    <span class="result-track-title">${title}</span>
    <span class="result-track-artist">${artist}</span>
    <span class="result-track-length">${duration_m}:${duration_s}</span>
    <div class="play-container"></div>
</div>`);
				}

				$track.data("uri", uri);
				$(".result-playlist-body").append($track);
				track_uris.push(uri);
			}
			loadingScreen.finish();
		},
		error: function (response, status, error) {
			console.log(response.status);
			console.log("response: " + response);
			console.log("error: " + error);
			switch (response.status) {
				case 401:
					console.log("401 Auth Error");
					var cookies = document.cookie.split(";");
					for (var i = 0; i < cookies.length; i++) {
						eraseCookie(cookies[i].split("=")[0]);
					}
					break;
				case 404:
					// console.log('404 Error Not Found');
					// document.html = '<h1>HIHIHI</h1>'
					// $('html').html('<h1>Sorry, couldn\'t find that playlist.</h1><br/><a href="/">Return home.</a>')
					$("body").html(`
<div id="notfound">
    <div class="notfound-bg">
        <div></div>
        <div></div>
        <div></div>
        <div></div>
    </div>
    <div class="notfound">
        <div class="notfound-404">
            <h1>404</h1>
        </div>
        <h2>Page Not Found</h2>
        <p>Opps, couldn't create a customized playlist from that.</p>
        <!-- <a href="/">Return home</a> -->
        <a href="/" class="link">
            <div class="button">Return home</div>
        </a>
    </div>
</div>`);

					// window.location.replace('/error');
					break;
				default:
					break;
			}
			loadingScreen.finish();
		},
	});

	$(document).on("click", ".player-button", function () {
		let this_button = $(this);
		let this_audio = $(this).parent().find("audio")[0];

		if ($(".player-button.pause-icon").not(this_button).length) {
			let prev_button = $(".player-button.pause-icon").not(this_button);
			let prev_audio = $(".player-button.pause-icon").parent().find("audio")[0];
			prev_button.toggleClass("play-icon pause-icon");
			prev_audio.pause();
		}
		this_button.toggleClass("play-icon pause-icon");
		this_audio.paused ? this_audio.play() : this_audio.pause();
	});

	device = "";

	// window.onSpotifyWebPlaybackSDKReady = () => {
	//     console.log('hi');
	//     const token = appConfig.access_token;
	//     console.log(token);
	//     const player = new Spotify.Player({
	//         name: 'Kabloombox',
	//         getOAuthToken: cb => { cb(token); }
	//     });

	//     // Error handling
	//     player.addListener('initialization_error', ({ message }) => { console.error(message); });
	//     player.addListener('authentication_error', ({ message }) => { console.error(message); });
	//     player.addListener('account_error', ({ message }) => { console.error(message); });
	//     player.addListener('playback_error', ({ message }) => { console.error(message); });

	//     // Playback status updates
	//     player.addListener('player_state_changed', state => { console.log(state); });

	//     // Ready
	//     player.addListener('ready', ({ device_id }) => {
	//         console.log('Ready with Device ID', device_id);
	//         device = device_id;

	//         // headers = {
	//         //     'Authorization': 'Bearer ' + token;
	//         // }
	//         // params = {
	//         //     'context_uri': uri,
	//         //
	//         // }

	//     });

	//     // Not Ready
	//     player.addListener('not_ready', ({ device_id }) => {
	//         console.log('Device ID has gone offline', device_id);
	//     });

	//     // Connect to the player!
	//     player.connect();
	// };

	// $('body').delegate('.result-playlist-track','click',function() {
	//     console.log('blah');
	//     // alert(1);
	//     $.post('http://localhost:8080/play?uri=' + $('.result-playlist-track').data('uri'));
	// });

	// play the song that the user clicked on using its uri
	// $('body').on('click', '.result-playlist-track', function() {
	//     console.log('thing');
	//     console.log($('.result-playlist-track').data('uri'));
	//     $.ajax({
	//         url: '/api/play',
	//         type: 'POST',
	//         dataType: 'json',
	//         contentType: 'application/json',
	//         data: JSON.stringify({
	//             'uri': $('.result-playlist-track').data('uri'),
	//             'device_id': device
	//         }),
	//         success: function(results) {
	//             console.log('play success');
	//
	//         },
	//         error: function(response, status, error) {
	//             console.log(response.status);
	//             console.log(error);
	//
	//             let json = JSON.parse(JSON.stringify(response));
	//             console.log(json.responseText);
	//
	//             switch(response.status) {
	//
	//                 case 401:
	//                     console.log('401 Auth Error');
	//                     var cookies = document.cookie.split(";");
	//                     for (var i = 0; i < cookies.length; i++) {
	//                         eraseCookie(cookies[i].split("=")[0]);
	//                     }
	//                     break;
	//                 case 404:
	//                     // $('html').html('<h1>Sorry, couldn\'t create that playlist.</h1><br/><a href="/">Return home.</a>')
	//                     // window.location.replace('/error');
	//                     break;
	//                 default:
	//                     break
	//             }
	//             loadingScreen.finish();
	//         }
	//     });
	// });

	/*Dropdown Menu*/
	$(".dropdown").click(function () {
		$(this).attr("tabindex", 1).focus();
		$(this).toggleClass("active");
		$(this).find(".dropdown-menu").slideToggle(300);
		// $('#arrow').rotate({ endDeg:180, persist:true });

		$("#arrow").animate(
			{ deg: 180 },
			{
				duration: 70,
				step: function (now) {
					$(this).css({ transform: "rotate(" + now + "deg)" });
				},
			}
		);
	});

	$(".dropdown").focusout(function () {
		$(".dropdown").removeClass("active");
		$(".dropdown").find(".dropdown-menu").slideUp(300);

		$("#arrow").animate(
			{ deg: 360 },
			{
				duration: 70,
				step: function (now) {
					$(this).css({ transform: "rotate(" + now + "deg)" });
				},
			}
		);
	});

	$(".result-playlist-add-button").click(function () {
		console.log($(".input-title").val());
		$.ajax({
			url: "/api/create",
			type: "POST",
			dataType: "json",
			contentType: "application/json",
			data: JSON.stringify({
				uris: track_uris.toString(),
				name: $(".input-title").val(),
			}),
			// data: track_uris.toString(),
			success: function (results) {
				console.log("success");
				console.log(results["message"]);
				loadingScreen.finish();
			},
			error: function (response, status, error) {
				console.log(response.status);
				console.log(error);

				let json = JSON.parse(JSON.stringify(response));
				console.log(json.responseText);

				switch (response.status) {
					case 401:
						console.log("401 Auth Error");
						var cookies = document.cookie.split(";");
						for (var i = 0; i < cookies.length; i++) {
							eraseCookie(cookies[i].split("=")[0]);
						}
						break;
					case 404:
						// $('html').html('<h1>Sorry, couldn\'t create that playlist.</h1><br/><a href="/">Return home.</a>')
						// window.location.replace('/error');
						break;
					default:
						break;
				}
				loadingScreen.finish();
			},
		});
	});
});

function on_playing_ended(el) {
	console.log("ended");
	$(el).parent().find(".player-button").toggleClass("play-icon pause-icon");
}

function forceTwoDigits(n) {
	return ("0" + n).slice(-2);
}
