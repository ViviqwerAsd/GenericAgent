# GenericAgent 新手上手指南

## 🎯 什么是 GenericAgent?

GenericAgent 是一个极简、可自我进化的自主 Agent 框架。它的核心只有 **~3,300 行代码**,通过 **7 个原子工具 + 92 行 Agent Loop**,就能赋予任意 LLM 对你本地计算机的系统级控制能力。

**它能做什么?**
- 控制浏览器(保留登录态)
- 执行终端命令
- 读写文件系统
- 模拟键盘鼠标
- 控制移动设备(ADB)
- 屏幕视觉识别

**最特别的是什么?**

GenericAgent 不预设技能,而是**靠进化获得能力**。每解决一个新任务,它就会自动将执行路径固化为 Skill,供后续直接调用。使用时间越长,沉淀的技能越多,最终形成一棵完全属于你的专属技能树。

> 🤖 **自举实证**: 本项目的所有 Git 操作,从 `git init` 到每一条 commit message,都是 GenericAgent 自主完成的。作者全程未打开过一次终端。

---

## 🚀 5 分钟快速开始

### 第一步:安装部署

**方法一:保留原有桌面 / Streamlit 方式**

```bash
# 1. 克隆仓库
git clone https://github.com/lsdefine/GenericAgent.git
cd GenericAgent

# 2. 安装 GUI 依赖
pip install streamlit pywebview

# 3. 启动原有桌面窗口
python launch.pyw
```

**方法二:新增 CLI 方式**

```bash
# 1. 克隆仓库
git clone https://github.com/lsdefine/GenericAgent.git
cd GenericAgent

# 2. 安装 CLI 依赖
pip install prompt_toolkit rich

# 3. 启动 CLI 新手引导
python cli.py
```

**方法三:Windows 便携版(推荐新手)**

1. [下载便携版](http://kw.fudan.edu.cn/resources/PC-Agent-Portable.zip) (19MB)
2. 解压到任意目录
3. 双击运行即可

**方法四:Android(Termux)**

```bash
cd /sdcard/ga
python agentmain.py
```

### 第二步:跟随引导完成配置

如果你使用新增的 CLI 入口，第一次运行 `python cli.py` 时，如果还没有可用模型，CLI 会直接进入新手引导：

- 先选择大模型厂商
- 再逐项填写 `apikey / apibase / model`
- 最后可选继续配置 Telegram、QQ、飞书、企业微信、钉钉机器人
  Telegram 会要求你填写自己的 `user_id`，其他平台仍可默认 `['*']`

配置完成后，CLI 会自动写入 `mykey.py`，不需要你手动复制模板文件。

支持的模型:
- Claude (Anthropic)
- GPT-4 / GPT-3.5 (OpenAI)
- Gemini (Google)
- Kimi (Moonshot)
- 其他兼容 OpenAI API 的模型

### 第三步:开始使用

这套 CLI 入口是新增能力，原来的桌面 / Streamlit 用法仍然保留不变。完成引导后，你会直接进入 CLI 界面。

```bash
python cli.py
```

后续你也可以在 CLI 里使用 `/model` 查看、切换或新增模型。

常用 CLI 能力：
- `/model`：查看、切换、新增、编辑、删除模型，以及设置默认模型
- `/chatbot`：查看机器人状态、启动/停止机器人、进入机器人配置
- `/auto`：开启或关闭空闲自主行动
- `/auto-now`：立刻触发一次空闲自主行动
- `/`：打开命令下拉补全

---

## 💡 基础使用

### 你的第一个任务

启动后,试试这些简单的任务:

**文件操作:**
```
"帮我在桌面创建一个 hello.txt 文件,内容是 Hello World"
```

**网页浏览:**
```
"打开百度,搜索今天的天气"
```

**代码执行:**
```
"用 Python 计算 1 到 100 的和"
```

### 理解 Agent 的工作方式

GenericAgent 的工作流程:

```
你的指令 → Agent 理解任务 → 调用工具执行 → 返回结果 → 沉淀经验
```

**核心循环(92 行代码):**
1. **感知**: 读取当前环境状态
2. **推理**: 分析任务,制定执行计划
3. **执行**: 调用工具完成操作
4. **记忆**: 将成功的执行路径写入记忆层
5. **循环**: 继续下一步,直到任务完成

---

## 🧬 进阶:Skill 系统

### 什么是 Skill?

Skill 是 GenericAgent 自动沉淀的任务执行模板。当你第一次完成某个任务时,Agent 会将整个执行流程固化为一个 Skill,下次遇到类似任务就能直接调用。

**举个例子:**

| 你说的话 | 第一次 Agent 做了什么 | 之后每次 |
|---------|---------------------|---------|
| "监控股票并提醒我" | 安装 mootdx → 构建选股流程 → 配置定时任务 → 保存 Skill | **一句话启动** |
| "用 Gmail 发这个文件" | 配置 OAuth → 编写发送脚本 → 保存 Skill | **直接可用** |

### 如何使用 Skill?

Skill 会自动保存在 `memory/` 目录下。你不需要手动管理,Agent 会在需要时自动调用。

**查看已有的 Skill:**
```bash
ls memory/*.md
```

**手动触发 Skill:**
```
"使用之前保存的股票监控 Skill"
```

### 培养你的专属 Agent

使用时间越长,你的 Agent 积累的 Skill 越多:

- **第 1 周**: 基础文件操作、简单网页浏览
- **第 1 个月**: 自动化工作流、数据处理脚本
- **第 3 个月**: 复杂的多步骤任务、跨平台操作
- **第 6 个月**: 一套任何人都没有的专属技能树

---

## 🎮 实用玩法

### 浏览器自动化

GenericAgent 注入真实浏览器,保留你的登录态:

```
"打开淘宝,搜索 iPhone 15,按价格排序"
"登录我的 Gmail,查看未读邮件"
"在美团上帮我点一杯奶茶"
```

**可用工具:**
- `web_scan`: 读取网页内容
- `web_execute_js`: 执行 JavaScript 控制页面

### 文件和代码处理

```
"分析这个 Python 项目的代码结构"
"把这个 CSV 文件转换成 Excel"
"批量重命名这个文件夹里的图片"
```

**可用工具:**
- `file_read`: 读取文件
- `file_write`: 写入文件
- `file_patch`: 精确修改文件
- `code_run`: 执行代码

### 移动设备控制(ADB)

通过 ADB 控制 Android 设备:

```
"打开支付宝,查看我的账单"
"在微信上给张三发消息"
"截取手机屏幕并保存"
```

### 定时任务

```
"每天早上 8 点提醒我查看邮件"
"每小时检查一次股票价格"
"每周一生成上周的工作总结"
```

---

## 🤖 接入聊天平台(可选)

### 为什么要接入 Bot?

将 GenericAgent 接入聊天平台后,你可以:
- 随时随地通过手机控制你的电脑
- 多人协作使用同一个 Agent
- 接收 Agent 的主动通知和提醒

### 支持的平台

- **QQ Bot**: WebSocket 长连接,无需公网 webhook
- **飞书(Lark)**: 支持富文本、图片、文件、音频
- **企业微信(WeCom)**: 企业内部使用
- **钉钉(DingTalk)**: 企业协作
- **Telegram**: 国际用户

### 快速配置指南

**以 QQ Bot 为例:**

1. 在 [QQ 开放平台](https://q.qq.com) 创建机器人
2. 获取 AppID 和 AppSecret
3. 在 `mykey.py` 中配置:

```python
qq_app_id = "YOUR_APP_ID"
qq_app_secret = "YOUR_APP_SECRET"
qq_allowed_users = ["*"]  # 可选，CLI 向导默认会填成 ['*']
```

4. 启动 Bot:

```bash
pip install qq-botpy
python qqapp.py
# 或与桌面窗口一起启动
python launch.pyw --qq
```

**其他平台配置详见:**
- 飞书: [assets/SETUP_FEISHU.md](assets/SETUP_FEISHU.md)
- 企业微信: `python launch.pyw --wecom`
- 钉钉: `python launch.pyw --dingtalk`
- Telegram: `python tgapp.py`

如果你已经在 CLI 里完成了机器人配置，也可以直接：

```bash
python cli.py
# 输入 /chatbot
```

然后在面板里查看状态、启动、停止或继续配置机器人。

---

## 📚 记忆系统详解

### 三层记忆架构

GenericAgent 的记忆系统分为三层:

**L0 — 元规则(Meta Rules)**
- Agent 的基础行为规则
- 系统约束和安全边界
- 不可修改的核心逻辑

**L2 — 全局事实(Global Facts)**
- 长期运行中积累的稳定知识
- 环境配置、用户偏好
- 存储在 `memory/global_mem.txt`

**L3 — 任务 Skills(SOPs)**
- 完成特定任务的操作流程
- 自动沉淀的执行模板
- 存储在 `memory/*.md`

### 如何查看和管理记忆

**查看全局记忆:**
```bash
cat memory/global_mem.txt
```

**查看所有 Skills:**
```bash
ls memory/*.md
```

**手动编辑记忆:**
```bash
# 不建议新手操作,Agent 会自动管理
vim memory/global_mem.txt
```

---

## 🔧 常见问题

### 安装问题

**Q: pip install 失败怎么办?**

A: 尝试使用国内镜像源:
```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple streamlit pywebview
```

**Q: Windows 上启动失败?**

A: 建议使用便携版,或检查 Python 版本(需要 3.8+)

### 使用问题

**Q: Agent 执行任务失败?**

A: 检查:
1. API Key 是否正确配置
2. 网络连接是否正常
3. 查看 `temp/` 目录下的日志文件

**Q: 如何让 Agent 停止当前任务?**

A: 在界面中输入 "停止" 或 "取消"

**Q: Agent 的回复太慢?**

A: 可以尝试:
1. 切换到更快的模型(如 GPT-3.5)
2. 减少任务的复杂度
3. 检查网络延迟

### 进阶问题

**Q: 如何自定义 Agent 的行为?**

A: 编辑 `memory/global_mem.txt`,添加你的偏好设置

**Q: 如何备份我的 Skills?**

A: 直接复制 `memory/` 目录即可

**Q: 可以同时运行多个 Agent 实例吗?**

A: 可以,但需要使用不同的工作目录

---

## 💪 最佳实践

### 新手建议

1. **从简单任务开始**: 先尝试文件操作、网页浏览等基础任务
2. **观察 Agent 的执行过程**: 理解它是如何调用工具的
3. **让 Agent 自己探索**: 不要过度干预,让它自主学习
4. **定期查看 Skills**: 了解 Agent 积累了哪些能力

### 进阶技巧

1. **组合使用多个工具**: 让 Agent 完成复杂的多步骤任务
2. **利用记忆系统**: 在 `global_mem.txt` 中记录常用的配置和偏好
3. **编写自定义脚本**: 通过 `code_run` 扩展 Agent 的能力
4. **接入多个聊天平台**: 实现跨平台的统一控制

### 安全注意事项

1. **不要在公共环境运行**: Agent 有系统级权限,注意安全
2. **谨慎授权**: QQ / 飞书 / 企业微信 / 钉钉在 CLI 新手向导里默认会写成 `['*']` 公开访问；Telegram 会要求你填写自己的 `user_id`
3. **定期备份**: 重要的 Skills 和配置要及时备份
4. **监控执行日志**: 定期检查 `temp/` 目录下的日志

---

## 🌟 社区和支持

### 获取帮助

- **GitHub Issues**: [提交问题](https://github.com/lsdefine/GenericAgent/issues)
- **微信交流群**: 扫描下方二维码加入

<div align="center">
<img src="assets/images/wechat_group.jpg" width="280"/>
</div>

### 贡献指南

欢迎贡献代码、文档或 Skills!

1. Fork 本仓库
2. 创建你的特性分支
3. 提交你的改动
4. 发起 Pull Request

---

## 📖 延伸阅读

- [完整 README](README.md) - 项目详细介绍
- [新用户欢迎文档](WELCOME_NEW_USER.md) - 详细的引导流程
- [快速开始指南](QUICK_START.pdf) - PDF 版本的快速入门
- [飞书配置指南](assets/SETUP_FEISHU.md) - 飞书 Bot 详细配置

---

**🎉 现在,开始你的 GenericAgent 之旅吧!**

记住: GenericAgent 不是一个预设好的工具,而是一个会随着你的使用不断进化的伙伴。使用时间越长,它就越懂你,越强大。
