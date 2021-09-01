import requests
from video.mp4 import MP4Stream


def visit(url):
    reader = MP4Stream()

    resp = requests.get(url, headers={"Range": f"bytes=0-{1024-1}"})
    if resp.status_code == 200:
        # server not support range
        reader.feed(resp.content)
    elif resp.status_code == 206:
        content_range = resp.headers.get("Content-Range")
        content_max = int(content_range.split("/")[-1])
        offset, req_len = reader.feed(resp.content, 0)
        while offset < content_max:
            resp = requests.get(
                url, headers={"Range": f"bytes={offset}-{offset+req_len-1}"}
            )
            offset, req_len = reader.feed(resp.content, offset)
    else:
        raise Exception(f"request error, status_code {resp.status_code}")
    return reader.get_meta()
