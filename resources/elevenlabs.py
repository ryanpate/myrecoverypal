"""Small ElevenLabs text-to-speech client for `manage.py generate_audio`.

Settings come from environment variables (only needed where the command
runs, e.g. a Railway shell; the web app never calls ElevenLabs):
    ELEVENLABS_API_KEY      required
    ELEVENLABS_VOICE_ID     required: the voice to use (copy its ID from
                            the ElevenLabs voice library)
    ELEVENLABS_MODEL_ID     optional, default eleven_multilingual_v2
    ELEVENLABS_OUTPUT_FORMAT optional, default mp3_44100_64. Must be an
                            mp3_44100_* format (resources/audio_mp3.py
                            stitches MPEG-1 frames); these work on every
                            ElevenLabs plan.
"""
import os
import time

import httpx

API_URL = 'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
DEFAULT_MODEL = 'eleven_multilingual_v2'
DEFAULT_FORMAT = 'mp3_44100_64'
# Calm, steady narration: a little slower than conversational speech.
VOICE_SETTINGS = {
    'stability': 0.6,
    'similarity_boost': 0.75,
    'style': 0.0,
    'use_speaker_boost': True,
    'speed': 0.92,
}
RETRY_STATUSES = {429, 500, 502, 503, 504}


class ElevenLabsError(RuntimeError):
    pass


class ElevenLabsConfig:
    def __init__(self, api_key=None, voice_id=None, model_id=None, output_format=None):
        self.api_key = api_key if api_key is not None else os.environ.get('ELEVENLABS_API_KEY', '')
        self.voice_id = voice_id if voice_id is not None else os.environ.get('ELEVENLABS_VOICE_ID', '')
        self.model_id = model_id or os.environ.get('ELEVENLABS_MODEL_ID') or DEFAULT_MODEL
        self.output_format = (output_format or os.environ.get('ELEVENLABS_OUTPUT_FORMAT')
                              or DEFAULT_FORMAT)

    def missing(self):
        return [name for name, value in (('ELEVENLABS_API_KEY', self.api_key),
                                         ('ELEVENLABS_VOICE_ID', self.voice_id)) if not value]


def synthesize(config, text, previous_text='', next_text='', client=None, retries=4):
    """Return MP3 bytes for `text`. previous_text/next_text keep the
    intonation consistent across separately generated segments."""
    if not config.output_format.startswith('mp3_44100'):
        raise ElevenLabsError('ELEVENLABS_OUTPUT_FORMAT must be an mp3_44100_* format')
    body = {'text': text, 'model_id': config.model_id, 'voice_settings': VOICE_SETTINGS}
    if previous_text:
        body['previous_text'] = previous_text
    if next_text:
        body['next_text'] = next_text
    own_client = client is None
    client = client or httpx.Client(timeout=120)
    try:
        for attempt in range(retries + 1):
            resp = client.post(
                API_URL.format(voice_id=config.voice_id),
                params={'output_format': config.output_format},
                headers={'xi-api-key': config.api_key, 'accept': 'audio/mpeg'},
                json=body,
            )
            if resp.status_code == 200:
                return resp.content
            if resp.status_code in RETRY_STATUSES and attempt < retries:
                time.sleep(min(30, 2 ** (attempt + 1)))
                continue
            raise ElevenLabsError(f'ElevenLabs returned {resp.status_code}: {resp.text[:300]}')
    finally:
        if own_client:
            client.close()
