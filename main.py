"""
AstrBot 三月七语句插件 v1.2.0

功能描述：
- 随机输出《崩坏·星穹铁道》三月七经典台词
- 支持用户自定义添加、删除、管理语句
- 用户级防刷屏与群聊日限机制

作者: HamLJYH
版本: 1.2.0
日期: 2026-06-26
"""

# 标准库
import os
import json
import time
import random
import functools
from typing import Dict, Any, AsyncGenerator, Tuple

# 第三方库
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

__version__ = "1.2.0"

# 常量
MAX_CONTENT_LENGTH = 500


def handle_errors(func):
    """统一错误处理装饰器"""
    @functools.wraps(func)
    async def wrapper(self, event: AstrMessageEvent, *args, **kwargs) -> AsyncGenerator[Any, None]:
        try:
            async for result in func(self, event, *args, **kwargs):
                yield result
        except ValueError as e:
            logger.warning(f"[{func.__name__}] 参数错误: {e}")
            yield event.plain_result(f"参数错误: {e}")
        except PermissionError:
            logger.error(f"[{func.__name__}] 权限不足")
            yield event.plain_result("权限不足，请检查文件权限")
        except Exception as e:
            logger.error(f"[{func.__name__}] 执行失败: {e}", exc_info=True)
            yield event.plain_result("操作失败，请稍后重试")
    return wrapper


@register("march7th_quotes", "YourName", "三月七语句插件", "1.2.0", "https://github.com/yourname/astrbot_plugin_march7th")
class March7thQuotesPlugin(Star):
    def __init__(self, context: Context, config: Dict[str, Any] = None):
        super().__init__(context)
        
        # 读取配置
        self.config = config or {}
        self.anti_spam_enabled = self.config.get("anti_spam_enabled", True)
        self.anti_spam_interval = self.config.get("anti_spam_interval", 10)
        self.group_daily_limit_enabled = self.config.get("group_daily_limit_enabled", True)
        self.group_daily_limit = self.config.get("group_daily_limit", 50)
        
        # 防刷屏记录
        self.user_cooldown: Dict[str, float] = {}
        
        # 群聊每日触发记录：{group_id: {"count": int, "date": str}}
        self.group_daily_count: Dict[str, Dict[str, Any]] = {}
        
        # 三月七默认语句库
        self.default_quotes = [
            {"content": "我的过去或许不在从前，而是在我的未来里，所以我一定会一站站走下去，哪怕有一天没有列车。", "source": "剧情台词"},
            {"content": "你好，我是三月七，今天也是充满希望的一天！", "source": "角色语音"},
            {"content": "我是三月七，如你所见，是一位美少女！", "source": "角色语音"},
            {"content": "本姑娘就是三月七，如假包换！", "source": "角色语音"},
            {"content": "哎呀，别这么严肃嘛，笑一个！", "source": "角色语音"},
            {"content": "我可是有照相机的人，什么场面没见过？", "source": "角色语音"},
            {"content": "记忆是照片，照片是记忆。", "source": "角色语音"},
            {"content": "虽然我不记得以前的事了，但现在的每一天都很开心！", "source": "剧情台词"},
            {"content": "列车上的大家，都是我的家人！", "source": "剧情台词"},
            {"content": "开拓者，要不要来拍张照？", "source": "角色语音"},
            {"content": "本姑娘出马，一个顶俩！", "source": "角色语音"},
            {"content": "遇到困难不要怕，微笑着面对它！", "source": "角色语音"},
            {"content": "我可是很厉害的，不要小看我哦！", "source": "角色语音"},
            {"content": "今天也要元气满满！", "source": "角色语音"},
            {"content": "我的照相机里，存满了大家的回忆呢。", "source": "角色语音"},
            {"content": "就算没有过去的记忆，我也要创造美好的未来！", "source": "剧情台词"},
            {"content": "嘿嘿，被我迷住了吧？", "source": "角色语音"},
            {"content": "三月七，出击！", "source": "角色语音"},
            {"content": "拍照可是我的强项，要摆什么姿势好呢？", "source": "角色语音"},
            {"content": "列车长帕姆说过，要保持乐观！", "source": "剧情台词"},
            {"content": "不管遇到什么，我都不会放弃的！", "source": "剧情台词"},
            {"content": "开拓者，你是我的最佳拍档！", "source": "剧情台词"},
            {"content": "我的箭，可是很准的！", "source": "角色语音"},
            {"content": "过去的记忆不重要，重要的是现在和你在一起的人。", "source": "剧情台词"},
            {"content": "我要把大家的笑容，都记录在相机里！", "source": "剧情台词"},
            {"content": "每一天都是新的开始，每一天都值得纪念！", "source": "角色语音"},
            {"content": "开拓者，我们去冒险吧！", "source": "角色语音"},
            {"content": "有我在，就不会让任何人受伤！", "source": "剧情台词"},
            {"content": "我的故事，从现在开始书写！", "source": "剧情台词"},
            {"content": "就算世界毁灭，我也要保护好大家！", "source": "剧情台词"},
            {"content": "三月七，永远十七岁！", "source": "角色语音"},
            {"content": "青春就是用来挥霍的，不对，是用来珍惜的！", "source": "角色语音"},
            {"content": "我可是很记仇的，哼！", "source": "角色语音"},
            {"content": "开拓者，你又惹我生气了！", "source": "角色语音"},
            {"content": "算了算了，本姑娘大人有大量，原谅你了。", "source": "角色语音"},
            {"content": "来，笑一个，茄子！", "source": "角色语音"},
            {"content": "这张照片，我要珍藏一辈子！", "source": "角色语音"},
            {"content": "记忆会消失，但照片不会。", "source": "剧情台词"},
            {"content": "我要成为最棒的列车护卫！", "source": "剧情台词"},
            {"content": "星穹列车，出发！", "source": "角色语音"},
            {"content": "宇宙这么大，我想去看看！", "source": "角色语音"},
            {"content": "每个星球都有不同的风景，太棒了！", "source": "剧情台词"},
            {"content": "开拓者，你觉得我穿哪件衣服好看？", "source": "角色语音"},
            {"content": "本姑娘天生丽质，穿什么都好看！", "source": "角色语音"},
            {"content": "哎呀，头发乱了，等我整理一下。", "source": "角色语音"},
            {"content": "我的弓箭可是很贵的，小心别弄坏了。", "source": "角色语音"},
            {"content": "战斗什么的，我最在行了！", "source": "角色语音"},
            {"content": "冰霜之箭，穿透黑暗！", "source": "角色语音"},
            {"content": "守护列车，守护大家，这就是我的使命！", "source": "剧情台词"},
            {"content": "就算没有星神的力量，我也要保护重要的人！", "source": "剧情台词"},
            {"content": "三月七，永不放弃！", "source": "角色语音"},
            {"content": "今天的我，也是超级可爱的！", "source": "角色语音"},
            {"content": "开拓者，你在看什么呢？", "source": "角色语音"},
            {"content": "找到了！吓死我了，还以为丢了。", "source": "角色语音"},
            {"content": "这张照片拍得真好，不愧是我！", "source": "角色语音"},
            {"content": "开拓者，我们来合个影吧！", "source": "角色语音"},
            {"content": "一二三，三月七！", "source": "角色语音"},
            {"content": "我的笑容，就是最强的武器！", "source": "角色语音"},
            {"content": "不管多强的敌人，我都不会退缩！", "source": "剧情台词"},
            {"content": "因为，我有要守护的人！", "source": "剧情台词"},
            {"content": "列车上的大家，一个都不能少！", "source": "剧情台词"},
            {"content": "帕姆，今天的列车清洁就交给我吧！", "source": "剧情台词"},
            {"content": "丹恒，别总是板着脸嘛。", "source": "剧情台词"},
            {"content": "瓦尔特先生，能给我讲讲以前的故事吗？", "source": "剧情台词"},
            {"content": "宇宙真奇妙，每天都有新发现！", "source": "剧情台词"},
            {"content": "开拓者，下次我们去哪个星球？", "source": "角色语音"},
            {"content": "我要把宇宙的美景，都拍下来！", "source": "剧情台词"},
            {"content": "这张拍得不好，重拍重拍！", "source": "角色语音"},
            {"content": "完美！这就是艺术！", "source": "角色语音"},
            {"content": "我的审美可是很高级的。", "source": "角色语音"},
            {"content": "三月七出品，必属精品！", "source": "角色语音"},
            {"content": "开拓者，你站那边，我站这边。", "source": "角色语音"},
            {"content": "对，就这样，保持微笑！", "source": "角色语音"},
            {"content": "咔嚓！完美的一张！", "source": "角色语音"},
            {"content": "我要把这张照片挂在列车里！", "source": "角色语音"},
            {"content": "大家看到一定会很开心的。", "source": "剧情台词"},
            {"content": "记忆虽然空白，但未来由我创造！", "source": "剧情台词"},
            {"content": "我不会被过去束缚，我要向前看！", "source": "剧情台词"},
            {"content": "每一天都是珍贵的礼物。", "source": "剧情台词"},
            {"content": "和大家的相遇，就是最好的记忆。", "source": "剧情台词"},
            {"content": "开拓者，谢谢你一直陪着我。", "source": "剧情台词"},
            {"content": "有你在，我就什么都不怕。", "source": "剧情台词"},
            {"content": "我们一起，去更远的地方吧！", "source": "剧情台词"},
            {"content": "星穹列车，永不止步！", "source": "剧情台词"},
            {"content": "三月七，永远在路上！", "source": "角色语音"},
            {"content": "我的冒险，才刚刚开始！", "source": "角色语音"},
            {"content": "未来有什么在等着我呢？好期待！", "source": "角色语音"},
            {"content": "不管前面有什么，一起面对吧！", "source": "剧情台词"},
            {"content": "我们是最好的伙伴，对吧？", "source": "剧情台词"},
            {"content": "那就说定了，永远不分开！", "source": "剧情台词"},
            {"content": "拉钩上吊，一百年不许变！", "source": "角色语音"},
            {"content": "嘿嘿，这样我们就约定好了。", "source": "角色语音"},
            {"content": "开拓者，你可不能反悔哦！", "source": "角色语音"},
            {"content": "反悔的人，要请我吃一个月的甜点！", "source": "角色语音"},
            {"content": "我最喜欢甜点了，尤其是蛋糕！", "source": "角色语音"},
            {"content": "列车上的甜点，都太好吃了。", "source": "角色语音"},
            {"content": "不过吃多了会胖的吧？", "source": "角色语音"},
            {"content": "算了，开心最重要！", "source": "角色语音"},
            {"content": "本姑娘天生吃不胖，羡慕吧？", "source": "角色语音"},
            {"content": "开拓者，你在偷笑什么？", "source": "角色语音"},
            {"content": "是不是觉得我很可爱？", "source": "角色语音"},
            {"content": "哼，算你有眼光！", "source": "角色语音"},
            {"content": "三月七，最可爱了！", "source": "角色语音"},
            {"content": "这是事实，不接受反驳！", "source": "角色语音"},
            {"content": "反驳的人，要给我拍一百张照片！", "source": "角色语音"},
            {"content": "开玩笑的啦，别当真。", "source": "角色语音"},
            {"content": "不过拍一百张也不是不行。", "source": "角色语音"},
            {"content": "我的相机内存很大的！", "source": "角色语音"},
            {"content": "能装下整个宇宙的回忆！", "source": "角色语音"},
            {"content": "这就是三月七，如你所见！", "source": "角色语音"},
            {"content": "一个热爱拍照、热爱冒险、热爱大家的女孩！", "source": "角色语音"},
            {"content": "请多关照啦，开拓者！", "source": "角色语音"},
        ]

        # 用户自定义语句文件路径
        self.custom_quotes_file = os.path.join(os.path.dirname(__file__), "custom_quotes.json")
        self.custom_quotes = self._load_custom_quotes()

        # 合并默认和用户自定义
        self.all_quotes = self.default_quotes + self.custom_quotes
        logger.info(f"三月七语句插件加载完成，共 {len(self.all_quotes)} 条语句（默认 {len(self.default_quotes)} 条，自定义 {len(self.custom_quotes)} 条）")

    def _load_custom_quotes(self) -> list:
        """加载用户自定义语句"""
        if os.path.exists(self.custom_quotes_file):
            try:
                with open(self.custom_quotes_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载自定义语句失败: {e}")
                return []
        return []

    def _save_custom_quotes(self) -> bool:
        """保存用户自定义语句"""
        try:
            with open(self.custom_quotes_file, "w", encoding="utf-8") as f:
                json.dump(self.custom_quotes, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存自定义语句失败: {e}")
            return False

    def _format_quote(self, quote: Dict[str, str], is_custom: bool = False) -> str:
        """格式化语句输出

        Args:
            quote: 语句字典，包含 content 和 source
            is_custom: 是否为自定义语句

        Returns:
            格式化后的字符串
        """
        content = quote.get("content", "")
        source = quote.get("source", "")
        
        result = "**三月七**"
        if source:
            result += " · *" + source + "*"
        if is_custom:
            result += " · [自定义]"
        result += "\n\n" + content
        return result

    def _get_today_str(self) -> str:
        """获取今天的日期字符串"""
        return time.strftime("%Y-%m-%d", time.localtime())

    def _clean_expired_records(self) -> None:
        """清理过期的用户记录（保留最近24小时）"""
        current_time = time.time()
        expire_time = current_time - 86400
        
        # 清理用户冷却记录
        expired_users = [
            uid for uid, t in self.user_cooldown.items() 
            if t < expire_time
        ]
        for uid in expired_users:
            del self.user_cooldown[uid]
        
        # 清理群聊计数记录（非今天的）
        today = self._get_today_str()
        expired_groups = [
            gid for gid, data in self.group_daily_count.items() 
            if data.get("date") != today
        ]
        for gid in expired_groups:
            del self.group_daily_count[gid]

    def _check_user_spam(self, user_id: str) -> Tuple[bool, str]:
        """检查用户是否触发个人防刷屏机制

        Args:
            user_id: 用户ID

        Returns:
            (是否允许触发, 提示信息)
        """
        if not self.anti_spam_enabled:
            return True, ""
        
        self._clean_expired_records()
        
        current_time = time.time()
        last_time = self.user_cooldown.get(user_id, 0)
        
        if current_time - last_time < self.anti_spam_interval:
            remaining = int(self.anti_spam_interval - (current_time - last_time))
            return False, f"触发太快了啦！请 {remaining} 秒后再试~"
        
        self.user_cooldown[user_id] = current_time
        return True, ""

    def _check_group_limit(self, group_id: str) -> Tuple[bool, str]:
        """检查群聊是否达到每日触发上限

        Args:
            group_id: 群聊ID

        Returns:
            (是否允许触发, 提示信息)
        """
        if not self.group_daily_limit_enabled:
            return True, ""
        
        self._clean_expired_records()
        
        today = self._get_today_str()
        
        if group_id not in self.group_daily_count:
            self.group_daily_count[group_id] = {"count": 0, "date": today}
        
        group_data = self.group_daily_count[group_id]
        
        # 如果日期不是今天，重置计数
        if group_data.get("date") != today:
            group_data = {"count": 0, "date": today}
            self.group_daily_count[group_id] = group_data
        
        if group_data["count"] >= self.group_daily_limit:
            return False, f"本群今天的三月七语句次数已经用完啦！明天再来吧~（上限: {self.group_daily_limit}次/天）"
        
        group_data["count"] += 1
        return True, ""

    def _validate_content(self, content: str) -> None:
        """验证语句内容

        Args:
            content: 待验证的内容

        Raises:
            ValueError: 内容不合法时抛出
        """
        if not content or not content.strip():
            raise ValueError("内容不能为空")
        if len(content) > MAX_CONTENT_LENGTH:
            raise ValueError(f"内容过长，最多 {MAX_CONTENT_LENGTH} 字符")

    @filter.command_group("三月七")
    def march7th_group(self):
        '''三月七语句插件指令组'''
        pass

    @handle_errors
    @march7th_group.command("语句")
    async def march7th_quote(self, event: AstrMessageEvent):
        '''随机输出一条三月七的语句'''
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id()) if event.get_group_id() else "private_" + user_id
        
        # 个人防刷屏检查
        allowed, msg = self._check_user_spam(user_id)
        if not allowed:
            yield event.plain_result(msg)
            return
        
        # 群聊每日限制检查
        allowed, msg = self._check_group_limit(group_id)
        if not allowed:
            yield event.plain_result(msg)
            return
        
        if not self.all_quotes:
            yield event.plain_result("暂无语句，请先使用 /三月七 添加 添加一些吧！")
            return

        quote = random.choice(self.all_quotes)
        is_custom = quote in self.custom_quotes
        yield event.plain_result(self._format_quote(quote, is_custom))

    @handle_errors
    @march7th_group.command("添加")
    async def add_quote(self, event: AstrMessageEvent):
        '''添加一条自定义三月七语句。用法: /三月七 添加 语句内容 [来源]'''
        # 从消息文本解析参数
        message = event.message_str
        # 去掉命令前缀
        if message.startswith("/三月七 添加"):
            args_str = message[len("/三月七 添加"):].strip()
        else:
            args_str = message[len("三月七 添加"):].strip()

        if not args_str or not args_str.strip():
            yield event.plain_result(
                "语句内容不能为空！\n"
                "用法: /三月七 添加 语句内容 [来源]\n"
                "示例: /三月七 添加 \"三月七最可爱啦！\" 角色语音"
            )
            return

        # 解析参数：支持引号包裹的内容
        if args_str.startswith('"') or args_str.startswith("'"):
            quote_char = args_str[0]
            end_idx = args_str.find(quote_char, 1)
            if end_idx != -1:
                new_content = args_str[1:end_idx].strip()
                new_source = args_str[end_idx+1:].strip()
            else:
                new_content = args_str.strip().strip('"').strip("'")
                new_source = ""
        else:
            parts = args_str.split(" ", 1)
            new_content = parts[0].strip()
            new_source = parts[1].strip() if len(parts) > 1 else ""

        # 验证内容
        self._validate_content(new_content)

        # 检查是否已存在
        for q in self.all_quotes:
            if q.get("content") == new_content:
                yield event.plain_result("这条语句已经存在啦！")
                return

        new_quote = {
            "content": new_content,
            "source": new_source
        }

        self.custom_quotes.append(new_quote)
        self.all_quotes = self.default_quotes + self.custom_quotes

        if self._save_custom_quotes():
            yield event.plain_result(
                "语句添加成功！\n\n"
                + self._format_quote(new_quote, is_custom=True) + "\n\n"
                + f"当前共有 {len(self.all_quotes)} 条语句（自定义 {len(self.custom_quotes)} 条）"
            )
        else:
            yield event.plain_result("语句添加失败，请检查文件权限。")

    @handle_errors
    @march7th_group.command("删除")
    async def delete_quote(self, event: AstrMessageEvent):
        '''删除包含指定关键词的自定义语句。用法: /三月七 删除 关键词'''
        # 从消息文本解析参数
        message = event.message_str
        if message.startswith("/三月七 删除"):
            keyword = message[len("/三月七 删除"):].strip()
        else:
            keyword = message[len("三月七 删除"):].strip()

        if not keyword or not keyword.strip():
            yield event.plain_result(
                "关键词不能为空！\n"
                "用法: /三月七 删除 关键词\n"
                "示例: /三月七 删除 开拓者"
            )
            return

        keyword = keyword.strip()

        # 只能删除自定义语句
        original_count = len(self.custom_quotes)
        self.custom_quotes = [
            q for q in self.custom_quotes 
            if keyword not in q.get("content", "")
        ]
        deleted_count = original_count - len(self.custom_quotes)

        if deleted_count == 0:
            yield event.plain_result("未找到包含「" + keyword + "」的自定义语句。\n注意：默认语句无法删除。")
            return

        self.all_quotes = self.default_quotes + self.custom_quotes

        if self._save_custom_quotes():
            yield event.plain_result(
                "已删除 " + str(deleted_count) + " 条包含「" + keyword + "」的语句。\n"
                + f"当前共有 {len(self.all_quotes)} 条语句（自定义 {len(self.custom_quotes)} 条）"
            )
        else:
            yield event.plain_result("删除失败，请检查文件权限。")

    @handle_errors
    @march7th_group.command("列表")
    async def list_quotes(self, event: AstrMessageEvent, page: int = 1):
        '''列出所有自定义语句。用法: /三月七 列表 [页码]'''
        if not self.custom_quotes:
            yield event.plain_result("暂无自定义语句。\n使用 /三月七 添加 来添加你的第一条语句吧！")
            return

        per_page = 10
        total_pages = (len(self.custom_quotes) + per_page - 1) // per_page

        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages

        start = (page - 1) * per_page
        end = start + per_page
        page_quotes = self.custom_quotes[start:end]

        result = "自定义语句列表（第 " + str(page) + "/" + str(total_pages) + " 页，共 " + str(len(self.custom_quotes)) + " 条）\n"
        result += "-" * 30 + "\n"

        for i, quote in enumerate(page_quotes, start=start + 1):
            content = quote.get("content", "")
            source = quote.get("source", "")
            # 截断过长的内容
            if len(content) > 30:
                content = content[:30] + "..."
            source_tag = " [" + source + "]" if source else ""
            result += str(i) + "." + source_tag + " " + content + "\n"

        if total_pages > 1:
            result += "\n使用 /三月七 列表 " + str(page + 1 if page < total_pages else 1) + " 翻页"

        yield event.plain_result(result)

    @handle_errors
    @march7th_group.command("统计")
    async def stats_quotes(self, event: AstrMessageEvent):
        '''查看语句统计信息'''
        # 统计各来源语句数量
        source_count: Dict[str, int] = {}
        for quote in self.all_quotes:
            src = quote.get("source", "未标注") or "未标注"
            source_count[src] = source_count.get(src, 0) + 1

        # 按数量降序，数量相同按来源名升序（保证稳定性）
        sorted_sources = sorted(source_count.items(), key=lambda x: (-x[1], x[0]))

        result = "三月七语句统计\n"
        result += "-" * 30 + "\n"
        result += "总语句数: " + str(len(self.all_quotes)) + "\n"
        result += "  - 默认语句: " + str(len(self.default_quotes)) + "\n"
        result += "  - 自定义语句: " + str(len(self.custom_quotes)) + "\n\n"

        result += "来源分布:\n"
        for src, count in sorted_sources:
            result += "  " + src + ": " + str(count) + "条\n"

        yield event.plain_result(result)

    @handle_errors
    @march7th_group.command("帮助")
    async def help_quotes(self, event: AstrMessageEvent):
        '''查看三月七语句插件帮助信息'''
        # 配置状态
        user_spam_status = "已开启" if self.anti_spam_enabled else "已关闭"
        user_spam_interval = f"{self.anti_spam_interval}秒" if self.anti_spam_enabled else "N/A"
        group_limit_status = "已开启" if self.group_daily_limit_enabled else "已关闭"
        group_limit = f"{self.group_daily_limit}次/天" if self.group_daily_limit_enabled else "N/A"
        
        help_lines = [
            "三月七语句插件",
            "",
            "配置信息:",
            "  用户防刷屏: " + user_spam_status + "（间隔: " + user_spam_interval + "）",
            "  群聊日限: " + group_limit_status + "（上限: " + group_limit + "）",
            "",
            "指令列表:",
            "------------------------------",
            "/三月七 语句 - 随机输出一条三月七语句",
            "/三月七 添加 <内容> [来源] - 添加自定义语句",
            "/三月七 删除 <关键词> - 删除包含关键词的自定义语句",
            "/三月七 列表 [页码] - 查看自定义语句列表",
            "/三月七 统计 - 查看语句统计信息",
            "/三月七 帮助 - 显示此帮助信息",
            "",
            "使用示例:",
            "------------------------------",
            "/三月七 语句",
            "-> 随机输出一条三月七语句",
            "",
            '/三月七 添加 "三月七最可爱啦！" 角色语音',
            "-> 添加一条带来源的语句",
            "",
            "/三月七 添加 开拓者是最好的伙伴",
            "-> 添加一条无来源的语句",
            "",
            "/三月七 删除 开拓者",
            "-> 删除所有包含\"开拓者\"的自定义语句",
            "",
            "/三月七 列表 2",
            "-> 查看第2页自定义语句",
            "",
            "注意事项:",
            "------------------------------",
            "- 默认语句无法删除，只能删除自定义语句",
            "- 自定义语句保存在插件目录的 custom_quotes.json 中",
            "- 添加语句时内容必填，来源可选",
            "- 防刷屏配置可在 AstrBot 插件配置中修改",
        ]
        help_text = "\n".join(help_lines)
        yield event.plain_result(help_text)

    async def terminate(self):
        '''插件卸载时保存数据'''
        self._save_custom_quotes()
        logger.info("三月七语句插件已卸载，数据已保存。")