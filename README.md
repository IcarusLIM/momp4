# Get Video Duration of A .mp4 File

Extract metadata of .mp4 video that corresponded by the given link

Instead of entire file, download the necessary data only

The video server should support [range](https://developer.mozilla.org/zh-CN/docs/Web/HTTP/Headers/Range)

## Usage

```python
from utils import visit

print(visit("https://media.vipkidstatic.com/prt/video/tools/upload/R6BrV8OZVZEzY.mp4"))
```

returns

```python
({'ftyp': {'major_band': 'mp42', 'minor_version': 0, 'compatible_brands': ['mp42', 'mp41']}, 'meta': {'version': 0, 'flags': b'\x00\x00\x00', 'creation_time': datetime.datetime(2087, 3, 9, 16, 0, 37), 'modification_time': datetime.datetime(2087, 3, 9, 16, 1, 11), 'time_scale': 90000, 'duration': 6624000, 'rate': 1.0, 'volume': 1.0, 'length': 73.6}}, True)
```

look into [demo.py](https://github.com/xyty007/momp4/blob/master/demo.py) for detail

## Methods

methods about video.mp4.MP4Stream

- **feed(bytes[, offset])**  
    feed bytes to parser  
    return offset to read next time and the length of byte suggested to read

- **get_meta()**  
    get parsed metadata  
    return (metadata, is done and ready to exit)