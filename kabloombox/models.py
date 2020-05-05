class TrackID(object):
    def __init__(self, value, language):
        self.value = value
        self.language = language

    @staticmethod
    def from_dict(source):
        return TrackID(
            value = source['value'],
            language = source['language']
        )

    def to_dict(self):
        return {
            'value': self.value,
            'language': self.language,
        }

    def __repr__(self):
        return f'TrackID(value={self.value}, language={self.language})'


class PlaylistID(object):
    def __init__(self, value, language):
        self.value = value
        self.language = language

    @staticmethod
    def from_dict(source):
        return PlaylistID(
            value=source['value'],
            language=source['language'],
        )

    def to_dict(self):
        return {
            'value': self.value,
            'language': self.language,
        }

    def __repr__(self):
        return f'TrackID(value={self.value}, language={self.language})'


class Track(object):
    def __init__(self, track_id, language, loudness, tempo, danceability,
        energy, acousticness, instrumentalness, liveness, valence, mode,
        speechiness):
        self.track_id = track_id
        self.language = language
        self.loudness = loudness
        self.tempo = tempo
        self.danceability = danceability
        self.energy = energy
        self.acousticness = acousticness
        self.instrumentalness = instrumentalness
        self.liveness = liveness
        self.valence = valence
        self.mode = mode
        self.speechiness = speechiness

    @staticmethod
    def from_dict(source):
        return Track(
            track_id=source['loudness'],
            language=source['language'],
            loudness=source['loudness'],
            tempo=source['tempo'],
            danceability=source['danceability'],
            energy=source['energy'],
            acousticness=source['acousticness'],
            instrumentalness=source['instrumentalness'],
            liveness=source['liveness'],
            valence=source['valence'],
            mode=source['mode'],
            speechiness=source['speechiness'])


    def to_dict(self):
        return {
            'loudness': self.loudness,
            'tempo': self.tempo,
            'danceability': self.danceability,
            'energy': self.energy,
            'acousticness': self.acousticness,
            'instrumentalness': self.instrumentalness,
            'liveness': self.liveness,
            'valence': self.valence,
            'mode': self.mode,
            'speechiness': self.speechiness,
        }

    def __repr__(self):
        return (f'''Track(loudness={self.loudness}), tempo={self.tempo},
        danceability={self.danceability}, energy={self.energy},
        acousticness={self.acousticness},
        instrumentalness={self.instrumentalness}, liveness={self.liveness},
        valence={self.valence}, mode={self.mode},
        speechiness={self.speechiness}''')

#
# class TrackObj:
#     def __init__(self, loudness, tempo, danceability, energy, acousticness, instrumentalness, liveness, valence, mode):
#         self.loudness = loudness
#         self.tempo = tempo
#         self.danceability = danceability
#         self.energy = energy
#         self.acousticness = acousticness
#         self.instrumentalness = instrumentalness
#         self.liveness = liveness
#         self.valence = valence
#         self.mode = mode