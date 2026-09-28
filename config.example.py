# ========== 目标网站 ==========
LOGIN_URL = "https://your-site.com/#/login"
SEARCH_PAGE_URL = "https://your-site.com/#/your-page"

# ========== 登录账号 ==========
USERNAME = "your_username"
PASSWORD = "your_password"

# ========== Excel 配置 ==========
EXCEL_FILE = r"path/to/your.xlsx"    # 运行前请关闭这个 Excel 文件
SHEET_NAME = "Sheet1"
SEARCH_COLUMN = "D"      # 从哪一列读取搜索关键词
START_ROW = 2            # 起始行
END_ROW = 0              # 结束行，0 表示读到该列最后一个有数据的行
RESULT_COLUMN = "H"      # 结果写回哪一列

# ========== 查询条件 ==========
VIN = "your_vin"
QUERY_WAIT = 3           # 点击查询后等待秒数

# ========== 验证码 ==========
CAPTCHA_MAX_RETRY = 8    # 识别失败最多重试次数

# ========== 浏览器显示 ==========
HEADLESS = True          # True: 后台运行不弹窗; False: 显示浏览器窗口