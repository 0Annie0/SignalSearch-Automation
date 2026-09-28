import logging
import sys

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from config import (
    EXCEL_FILE, SHEET_NAME, SEARCH_COLUMN, START_ROW, END_ROW,
    RESULT_COLUMN, VIN, USERNAME, PASSWORD, HEADLESS
)
from utils.excel_helper import load_keywords, write_results
from pages.login_page import LoginPage
from pages.search_page import SearchPage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    # ---------- 1. 读取 Excel ----------
    logger.info("开始读取 Excel: %s", EXCEL_FILE)
    keywords = load_keywords(EXCEL_FILE, SHEET_NAME, SEARCH_COLUMN, START_ROW, END_ROW)
    if not keywords:
        logger.error("没有读到任何关键词，请检查 SHEET_NAME / SEARCH_COLUMN / START_ROW")
        sys.exit(1)
    logger.info("共读取 %d 条待搜索内容", len(keywords))

    # ---------- 2. 启动浏览器 ----------
    options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless=new")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    if not HEADLESS:
        driver.maximize_window()

    results = []
    try:
        # ---------- 3. 登录 ----------
        login_page = LoginPage(driver)
        login_page.login(USERNAME, PASSWORD)

        # ---------- 4. 进入搜索页，先查 VIN ----------
        search_page = SearchPage(driver)
        search_page.open()
        search_page.wait_ready()
        search_page.query_by_vin(VIN)

        # ---------- 5. 逐条匹配 ----------
        for row, keyword in keywords:
            ok = search_page.contains(keyword)
            results.append((row, keyword, ok))
            logger.info("第 %d 行 [%s] -> %s", row, keyword, "PASS" if ok else "FAIL")

    finally:
        driver.quit()
        logger.info("浏览器已关闭")

    # ---------- 6. 汇总 ----------
    total = len(results)
    passed = sum(1 for _, _, ok in results if ok)
    logger.info("========== 汇总 ==========")
    logger.info("总数: %d, PASS: %d, FAIL: %d", total, passed, total - passed)

    # ---------- 7. 写回原 Excel ----------
    if RESULT_COLUMN:
        try:
            write_results(EXCEL_FILE, SHEET_NAME, RESULT_COLUMN, results)
            logger.info("结果已写回: %s 的 %s 列", EXCEL_FILE, RESULT_COLUMN)
        except PermissionError:
            logger.error("❌ 写回失败：请先关闭 Excel 文件后再运行！")
            for row, kw, ok in results:
                logger.info("[手动补写] 第 %d 行 -> %s", row, "PASS" if ok else "FAIL")
        except Exception as e:
            logger.error("写回 Excel 出错: %s", e)


if __name__ == "__main__":
    main()