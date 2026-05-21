import urllib.request
import urllib.parse
import json

# python3 -m py_compile Tahcia.py tahcia_client.py

class TahciaClient:
    def __init__(self, api_key):
        self.api_url = "https://api.tahcia.com"
        self.api_key = api_key

    def _get_headers(self):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        if self.api_key:
            headers['Authorization'] = 'Bearer {}'.format(self.api_key)
        return headers

    def list_scripts(self):
        url = "{}/ide/scripts/@me/list".format(self.api_url)
        req = urllib.request.Request(url, headers=self._get_headers(), method='GET')
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            raise RuntimeError("Failed to list remote scripts: {}".format(e))

    def download_script(self, name):
        encoded_name = urllib.parse.quote(name)
        url = "{}/ide/scripts/@me/{}".format(self.api_url, encoded_name)
        req = urllib.request.Request(url, headers=self._get_headers(), method='GET')
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data.get('content', '')
        except Exception as e:
            raise RuntimeError("Failed to download script '{}': {}".format(name, e))

    def upload_script(self, name, code):
        encoded_name = urllib.parse.quote(name)
        url = "{}/ide/scripts/@me/{}".format(self.api_url, encoded_name)
        payload = json.dumps({'code': code}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers=self._get_headers(), method='PUT')
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            raise RuntimeError("Failed to upload script '{}': {}".format(name, e))

    def delete_script(self, name):
        encoded_name = urllib.parse.quote(name)
        url = "{}/ide/scripts/@me/{}".format(self.api_url, encoded_name)
        req = urllib.request.Request(url, headers=self._get_headers(), method='DELETE')
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            raise RuntimeError("Failed to delete script '{}': {}".format(name, e))
