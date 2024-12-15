from .common import InfoExtractor
from ..utils import traverse_obj
import requests
import os
import json
import time
from hashlib import sha1
from base64 import b64decode
import xml.etree.ElementTree as ET
from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH

class ToggoIE(InfoExtractor):
    IE_NAME = 'toggo'
    _VALID_URL = r'https?://www\.toggo\.de/([a-z0-9-]+)/([a-z0-9-]+)/(?P<id>[a-z0-9-_]+)'
    _TESTS = [{
        'url': 'https://www.toggo.de/weihnachtsmann--co-kg/folge/ein-geschenk-fuer-zwei',
        'info_dict': {
            'id': 'VEP2977',
            'ext': 'mp4',
            'title': 'Ein Geschenk für zwei',
            'display_id': 'ein-geschenk-fuer-zwei',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'description': 'md5:b7715915bfa47824b4e4ad33fb5962f8',
            'release_timestamp': 1637259179,
            'series': 'Weihnachtsmann & Co. KG',
            'season': 'Weihnachtsmann & Co. KG',
            'season_number': 1,
            'season_id': 'VST118',
            'episode': 'Ein Geschenk für zwei',
            'episode_number': 7,
            'episode_id': 'VEP2977',
            'timestamp': 1581935960,
            'uploader_id': '6057955896001',
            'upload_date': '20200217',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.toggo.de/grizzy--die-lemminge/folge/ab-durch-die-wand-vogelfrei-rock\'n\'lemming',
        'only_matching': True,
    }, {
        'url': 'https://www.toggo.de/toggolino/paw-patrol/folge/der-wetter-zeppelin-der-chili-kochwettbewerb',
        'only_matching': True,
    }, {
        'url': 'https://www.toggo.de/toggolino/paw-patrol/video/paw-patrol-rettung-im-anflug',
        'only_matching': True,
    }]

    _toggo_basic_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Origin': 'https://www.toggo.de',
        'Referer': 'https://www.toggo.de/',
    }

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
            **self._toggo_basic_headers,
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

    def _extract_info(self, video_id):
        video_data = self._download_json(
            'https://production-n.toggo.de/api/assetstore/vod/asset/' + video_id,
            video_id,
            headers={**self._toggo_basic_headers},
            note='Downloading video metadata'
        )

        info_dict = {
            'id': video_id,
            'title': traverse_obj(video_data, ('data', 'title')),
            'description': traverse_obj(video_data, ('data', 'descriptionV2')),
            'thumbnail': traverse_obj(video_data, ('data', 'images', 'Thumbnail'))
        }

        return info_dict
    
    def _extract_formats(self, video_id):
        video_formats = self._download_json(
            'https://production-n.toggo.de/api/entitlement/play',
            video_id,
            data=json.dumps({
                'asset_id': video_id,
                'type': 'VideoAsset',
                'current_time': int(time.time()),
                'isRtlTech': True
            }).encode(),
            headers={**self._toggo_basic_headers,
                'Content-Type': 'application/json',
                'X-Adobe-Target': 'ATAT-97-B',
                'X-Authorized-User': 'false',
                'X-Device-Id': '286e37c7-53a4-a79b-4969-f5f38499c6f8',
                'X-Paid-User': 'false',
                'X-Platform-Type': 'Web',
                'X-Preview-Mode': 'false'},
            note='Downloading video formats'
        )

        license_server_url = traverse_obj(video_formats, ('data', 'player_data', 0, 'licenses', 0, 'uri', 'href'))
        pssh = []

        for playout_variant in traverse_obj(video_formats, ('data', 'player_data')):
            if traverse_obj(playout_variant, 'name') in ['dashsd', 'dashhd']:
                for playout in traverse_obj(playout_variant, ('sources')):
                    mpd_url = traverse_obj(playout, ('url'))
                    pssh.append(self._get_widevine_pssh(mpd_url, video_id))

        if len(set(pssh)) != 1:
            raise ValueError('Multiple PSSH values found.')

        key_pairs = self._get_widevine_license(video_id, license_server_url, pssh[0])

        formats = []
        for playout_variant in traverse_obj(video_formats, ('data', 'player_data')):
            if traverse_obj(playout_variant, 'name') in ['dashsd', 'dashhd']:
                for playout in traverse_obj(playout_variant, ('sources')):
                    mpd_url = traverse_obj(playout, ('url'))
                    fmts = self._extract_mpd_formats(mpd_url, video_id)

                    for fmt in fmts:
                        if 'has_drm' in fmt and 'kid' in fmt:
                            formatted_kid = fmt['kid'].replace('-', '').lower()
                            for key_pair in key_pairs:
                                if key_pair['kid'].lower() == formatted_kid:
                                    fmt['has_drm'] = False
                                    fmt['dash_cenc'] = key_pair
                                    break

                    formats.extend(fmts)

        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)

        info_dict = self._extract_info(video_id)

        formats = self._extract_formats(video_id)

        return {
            **info_dict,
            'formats': formats,
        }
