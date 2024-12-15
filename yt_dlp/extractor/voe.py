from .common import InfoExtractor

class VoeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?voe\.sx/(e/)?(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'https://voe.sx/czvp2pmdqnva',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': 'czvp2pmdqnva',
            'ext': 'mp4',
            'title': 'The.Americans.S01E02.GERMAN.FORCED.720p.WEB.H264.INTERNAL-RWP.mp4',
            'description': 'md5:somehashvalue',
            'uploader': 'md5:somehashvalue',
        }
    }]

    def _extract_info(self, video_id, webpage):
        # Extract title
        title = self._html_search_regex(r'<meta name="og:title" content="(.+?)\.?[^\"\s\s.]+">', webpage, 'title')

        # Extract description
        description = self._og_search_description(webpage)

        # Extract thumbnail
        thumbnail = self._og_search_thumbnail(webpage)

        info_dict = {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail
        }

        return info_dict
    
    def _extract_formats(self, video_id, webpage):
        # Extract m3u8 URL
        m3u8_url = self._search_regex(
            r'let nodeDetails = prompt\("Node", "([^"]+\.m3u8[^"]+)"\);',
            webpage,
            'm3u8 URL'
        )

        # Extract formats using _extract_m3u8_formats
        formats = self._extract_m3u8_formats(m3u8_url, video_id, fatal=True, m3u8_id='hls')

        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(f'https://voe.sx/{video_id}', video_id)

        # Handle redirect
        redirect_url = self._html_search_regex(r'window.location.href = \'(.+?)\';', webpage, 'redirect_url')

        # Download new webpage
        new_webpage = self._download_webpage(redirect_url, video_id)

        info_dict = self._extract_info(video_id, new_webpage)

        formats = self._extract_formats(video_id, new_webpage)

        return {
            **info_dict,
            'formats': formats,
        }