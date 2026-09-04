"""平台适配器包入口。"""

from app.publisher.adapters.toutiao import ToutiaoAdapter
from app.publisher.adapters.baijiahao import BaijiahaoAdapter
from app.publisher.adapters.zhihu import ZhihuAdapter
from app.publisher.adapters.penguin import PenguinAdapter
from app.publisher.adapters.xhs import XhsAdapter

ADAPTERS = {
    "toutiao": ToutiaoAdapter,
    "baijiahao": BaijiahaoAdapter,
    "zhihu": ZhihuAdapter,
    "penguin": PenguinAdapter,
    "xhs": XhsAdapter,
}