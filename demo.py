import requests
from video.mp4 import MP4Stream

# download video
resp = requests.get(
    "https://media.vipkidstatic.com/prt/video/tools/upload/R6BrV8OZVZEzY.mp4",
)
with open("test.mp4", "wb") as f:
    f.write(resp.content)

mp4 = MP4Stream()
print("\n*************************************\n")
with open("test.mp4", "rb") as f:
    offset = 0
    read_len = 1024
    while True:
        print(f"read byte range: {offset}~{offset+read_len}")
        f.seek(offset, 0)
        bytess = f.read(read_len)
        if not bytess:
            break
        offset, read_len = mp4.feed(bytess, offset)
print("\n*************************************\n")

res = mp4.get_meta()
print(f"is contact: {res[1]}\n\nmetadata:\n", res[0])
