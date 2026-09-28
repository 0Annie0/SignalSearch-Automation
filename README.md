# 企标数据上报自动化校验脚本

基于 Python + Selenium 的 Web UI 自动化脚本，用于批量校验 B 端平台中信号数据是否上报成功。

## 背景

在车企智能网联部门的日常测试工作中，"企标数据上报"模块需要人工逐条输入 signal_id 到平台查询，核对返回结果是否包含目标信号。单轮 90 条信号校验耗时约 30 分钟，重复性高、易遗漏。

本项目将该流程自动化：从 Excel 读取待校验的 signal_id，自动登录平台、输入 VIN 查询、逐条匹配目标信号，并将 PASS / FAIL 结果回写到原 Excel。

## 技术栈

- **Python 3.10**
- **Selenium 4**：浏览器自动化
- **webdriver-manager**：自动管理 ChromeDriver
- **openpyxl**：Excel 读写
- **ddddocr**：算术验证码识别（含图像预处理与映射规则）

## 项目结构

CompanyStandardLookup/
├── main.py # 主入口
├── config.py # 本地配置（不提交）
├── config.example.py # 配置模板
├── requirements.txt
├── pages/
│ ├── login_page.py # 登录页对象（含验证码识别重试）
│ └── search_page.py # 搜索页对象（含精确匹配）
└── utils/
├── captcha.py # 验证码识别（ddddocr + 图像预处理）
└── excel_helper.py # Excel 读写
text


## 核心功能

1. 从 Excel 指定 sheet、指定列、指定行范围读取关键词
2. 自动登录门户（含算术验证码识别，识别失败自动刷新重试）
3. 自动进入查询页，按 VIN 查询数据
4. 在页面可见文本中精确匹配关键词（忽略大小写，前后边界校验）
5. 将结果写回原 Excel，FAIL 行红底黑字
6. 支持无头模式后台运行

## 验证码识别思路

平台登录页使用**算术验证码**（如 `7*5=?`），字符为蓝色扭曲艺术字，通用 OCR 难以识别。方案：

1. 从验证码图片的 base64 中解码原图
2. 通过颜色阈值提取蓝色字符，转为黑底白字
3. 尝试多种预处理（原图 / 蓝色提取 / 反色，放大 3x / 4x）
4. 用 `ddddocr` 两个模型分别识别
5. 将 OCR 结果通过映射表规范为 `[数字][运算符][数字]` 形式（例如 `十`→`+`，`人`→`+`，`l`→`/`）
6. 求值后填入输入框，失败则刷新验证码重试（最多 8 次）

## 安装

```bash
pip install -r requirements.txt

使用

    复制配置模板并填写真实信息：
    bash

    copy config.example.py config.py

    编辑 config.py，填入登录 URL、账号、Excel 路径、VIN 等。

    关闭要写入的 Excel 文件（openpyxl 无法写入已打开的文件）。

    运行：
    bash

    python main.py

    脚本会将 PASS / FAIL 写回原 Excel 的 RESULT_COLUMN 列。

配置说明
字段	说明
LOGIN_URL / SEARCH_PAGE_URL	登录页与查询页 URL
USERNAME / PASSWORD	登录账号
EXCEL_FILE	Excel 路径
SHEET_NAME	工作表名
SEARCH_COLUMN	读取关键词的列
START_ROW / END_ROW	读取的行范围（END_ROW=0 表示读到有数据的最后一行）
RESULT_COLUMN	结果写回的列
VIN	查询条件
QUERY_WAIT	点击查询后等待秒数
CAPTCHA_MAX_RETRY	验证码最大重试次数
HEADLESS	是否无头运行
亮点

    数据驱动：关键词来源于 Excel，无需改代码

    精确匹配：忽略大小写，同时用正则边界保证不会把 HVSM_FLSeatTempVD 误判成 HVSM_FLSeatTemp

    稳定的输入框填充：JS 聚焦 + JS 清空 + 输入后校验，兼容 Element UI 组件

    验证码多策略识别：颜色提取 + 多预处理 + 映射表 + 重试机制

    无头运行：一键切换后台模式，适合定时任务

License

MIT