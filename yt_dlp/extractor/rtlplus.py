from .common import InfoExtractor
from ..utils import traverse_obj
import requests
import os
import json
from hashlib import sha1
from base64 import b64decode
import xml.etree.ElementTree as ET
from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH

class PremiumRequired(Exception):
    pass

class RTLplusIE(InfoExtractor):
    _VALID_URL = r'https?://plus\.rtl\.de/video-tv/(serien|shows|filme)/([a-z0-9-]+)/([a-z0-9-]+)/([a-z0-9-]+)(?P<id>[0-9]{6})'
    _TESTS = [{
        'url': 'https://www.joyn.at/play/serien/the-voice-of-germany/14-4-blind-auditions-4-traenen-der-ruehrung-und-rock-n-roll',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': '14-4-blind-auditions-4-traenen-der-ruehrung-und-rock-n-roll',
            'ext': 'mp4',
        }
    }]

    _rtlp_graphql_url = 'https://cdn.gateway.now-plus-prod.aws-cbc.cloud/graphql'
    _rtlp_basic_headers = {
        'Accept': '*/*',
        'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
        'Origin': 'https://plus.rtl.de',
        'Referer': 'https://plus.rtl.de/',
        'Rtlplus-Client-Id': 'rci:rtlplus:web',
        'Rtlplus-Client-Version': '2024.7.29.2',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    _rtlp_auth_jwt = ''
    _rtlp_prem_bypass = False

    def _get_widevine_pssh(self, manifest_url, video_id):
        manifest = self._download_xml(manifest_url, video_id, note='Downloading Widevine manifest')

        namespaces = {'': 'urn:mpeg:dash:schema:mpd:2011', 'cenc': 'urn:mpeg:cenc:2013'}
        widevine_psshs = []
        
        for content_protection in manifest.findall(".//ContentProtection[@schemeIdUri='urn:uuid:EDEF8BA9-79D6-4ACE-A3C8-27DCD51D21ED']", namespaces):
            pssh_element = content_protection.find('cenc:pssh', namespaces)
            if pssh_element is not None:
                widevine_psshs.append(pssh_element.text)

        if len(set(widevine_psshs)) != 1:
            raise ValueError('Multiple Widevine PSSH values found.')

        self.write_debug(f'{video_id}: PSSH extraction successful')
        return widevine_psshs[0]
    
    def _get_widevine_license(self, video_id, license_server_url, widevine_pssh):
        self.write_debug(f'{video_id}: Getting Widevine license from server {license_server_url}')
        pssh = PSSH(widevine_pssh)

        device_certificate_path = 'device.wvd'
        if not os.path.isfile(device_certificate_path):
            raise ValueError('Device certificate not found. Ensure device.wvd exists.')

        device = Device.load(device_certificate_path)
        cdm = Cdm.from_device(device)
        session_id = cdm.open()
        
        self.write_debug(f'{video_id}: Creating license challenge for PSSH: {widevine_pssh[:30]}...')

        challenge = cdm.get_license_challenge(session_id, pssh)
        headers = {
            **self._rtlp_basic_headers,
            'X-Auth-Token': f'Bearer {self._rtlp_auth_jwt}',
        }

        response = requests.post(license_server_url, headers=headers, data=challenge)
        response.raise_for_status()
        cdm.parse_license(session_id, response.content)

        key_pairs = []
        for key in cdm.get_keys(session_id):
            if key.type == 'CONTENT':
                key_pairs.append({'kid': key.kid.hex, 'key': key.key.hex()})

        cdm.close(session_id)
        self.write_debug(f'{video_id}: Successfully retrieved keys: {key_pairs}')
        return key_pairs

    def _authenticate(self, video_id):
        if not self._rtlp_auth_jwt:
            auth_token_from_env = os.environ.get('RTLP_AUTH_JWT', None)
            
            if auth_token_from_env:
                self._rtlp_auth_jwt = auth_token_from_env
                self._rtlp_prem_bypass = True
                self.write_debug(f'{video_id}: Authentication successful using JWT from environment variable.')
                return
                
            self.write_debug('Authenticating anonymously...')

            auth_response = self._download_json(
                'https://auth.rtl.de/auth/realms/rtlplus/protocol/openid-connect/token',
                video_id,
                headers={
                    **self._rtlp_basic_headers,
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data=bytes('grant_type=client_credentials&client_id=anonymous-user&client_secret=4bfeb73f-1c4a-4e9f-a7fa-96aa1ad3d94c', 'utf-8'),
                note='Authenticating anonymously'
            )
            self._rtlp_auth_jwt = traverse_obj(auth_response, ('access_token'))
            self.write_debug(f'{video_id}: Authentication successful.')

    def _extract_info(self, video_id):
        video_data = self._download_json(
            self._rtlp_graphql_url,
            video_id,
            headers={**self._rtlp_basic_headers, 'Authorization': f'Bearer {self._rtlp_auth_jwt}'},
            query={
                'operationName': 'EpisodeDetail',
                'variables': json.dumps({'episodeId': f'rrn:watch:videohub:episode:{video_id}'}).encode(),
                'extensions': json.dumps({
                    'persistedQuery': {'version': 1, 'sha256Hash': '04e2f59b9c750df1137f9946258c17686cd4447511383ef05fcf699183f449b8'}
                }).encode()
            },
            note='Downloading video metadata'
        )

        tier = traverse_obj(video_data, ('data', 'episode', 'tier'))
        self.write_debug(f'{video_id}: Video tier: {tier}')
        if tier != 'FREE' and not self._rtlp_prem_bypass:
            raise PremiumRequired(f'Video {video_id} requires premium access.')

        info_dict = {
            'id': video_id,
            'title': traverse_obj(video_data, ('data', 'episode', 'title')),
            'description': traverse_obj(video_data, ('data', 'episode', 'descriptionV2')),
            'thumbnail': traverse_obj(video_data, ('data', 'episode', 'format', 'watchImages', 'plainLandscape', 'absoluteUri'))
        }

        return info_dict
    
    def _extract_formats(self, video_id):
        video_formats = self._download_json(
            self._rtlp_graphql_url,
            video_id,
            headers={**self._rtlp_basic_headers, 'Authorization': f'Bearer {self._rtlp_auth_jwt}'},
            query={
                'operationName': 'WatchPlayerConfigV3',
                'variables': json.dumps({'platform': 'WEB', 'id': f'rrn:watch:videohub:episode:{video_id}'}).encode(),
                'extensions': json.dumps({
                    'persistedQuery': {'version': 1, 'sha256Hash': 'fea0311fb572b6fded60c5a1a9d652f97f55d182bc4cedbdad676354a8d2797c'}
                }).encode()
            },
            note='Downloading video formats'
        )

        license_server_url = traverse_obj(video_formats, ('data', 'watchPlayerConfigV3', 'playoutVariants', -1, 'licenses', 0, 'licenseUrl'))
        pssh = []

        for playout_variant in traverse_obj(video_formats, ('data', 'watchPlayerConfigV3', 'playoutVariants')):
            if traverse_obj(playout_variant, 'type') in ['dashsd', 'dashhd']:
                for playout in traverse_obj(playout_variant, ('sources')):
                    mpd_url = traverse_obj(playout, ('url'))
                    pssh.append(self._get_widevine_pssh(mpd_url, video_id))

        if len(set(pssh)) != 1:
            raise ValueError('Multiple PSSH values found.')

        key_pairs = self._get_widevine_license(video_id, license_server_url, pssh[0])

        formats, subtitles = [], {}
        for playout_variant in traverse_obj(video_formats, ('data', 'watchPlayerConfigV3', 'playoutVariants')):
            if playout_variant.get('type') in ['dashsd', 'dashhd']:
                for playout in traverse_obj(playout_variant, ('sources')):
                    mpd_url = traverse_obj(playout, ('url'))
                    fmts, subs = self._extract_mpd_formats_and_subtitles(mpd_url, video_id)

                    for fmt in fmts:
                        if 'has_drm' in fmt and 'kid' in fmt:
                            formatted_kid = fmt['kid'].replace('-', '').lower()
                            for key_pair in key_pairs:
                                if key_pair['kid'].lower() == formatted_kid:
                                    fmt['has_drm'] = False
                                    fmt['dash_cenc'] = key_pair
                                    break

                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)

        return formats, subtitles

    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._authenticate(video_id)

        info_dict = self._extract_info(video_id)

        formats, subtitles = self._extract_formats(video_id)

        return {
            **info_dict,
            'formats': formats,
            'subtitles': subtitles
        }
