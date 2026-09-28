import re
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from config import SEARCH_PAGE_URL, QUERY_WAIT

logger = logging.getLogger(__name__)


class SearchPage:
    """VIN 查询页"""

    VIN_INPUT = (By.XPATH, "//input[@placeholder='请输入VIN码']")
    QUERY_BUTTON = (By.XPATH, "//button[.//span[normalize-space()='查询']]")

    def __init__(self, driver, wait: int = 20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait)

    def _safe_url(self) -> str:
        """脱敏：只保留域名和路径，去掉查询参数"""
        try:
            return self.driver.current_url.split("?")[0]
        except Exception:
            return ""

    def open(self) -> None:
        if SEARCH_PAGE_URL:
            logger.info("准备访问搜索页")
            self.driver.get(SEARCH_PAGE_URL)
            logger.info("当前 URL: %s", self._safe_url())
            logger.info("页面标题: %s", self.driver.title)
        else:
            logger.info("SEARCH_PAGE_URL 为空，不跳转")

    def wait_ready(self) -> None:
        try:
            self.wait.until(EC.presence_of_element_located(self.VIN_INPUT))
            logger.info("✅ 搜索页就绪，VIN 输入框已出现")
        except TimeoutException:
            logger.error("❌ 搜索页加载超时")
            logger.error("   当前 URL: %s", self._safe_url())
            logger.error("   页面标题: %s", self.driver.title)
            try:
                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                for i, el in enumerate(inputs):
                    logger.error("   input[%d] placeholder=%r type=%r",
                                 i,
                                 el.get_attribute("placeholder"),
                                 el.get_attribute("type"))
            except Exception:
                pass
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                logger.error("   页面里有 %d 个 iframe，元素可能在 iframe 内！", len(iframes))
            raise

    def query_by_vin(self, vin: str) -> None:
        vin_input = self.wait.until(EC.element_to_be_clickable(self.VIN_INPUT))
        vin_input.click()
        vin_input.send_keys(Keys.CONTROL, "a")
        vin_input.send_keys(Keys.DELETE)
        vin_input.send_keys(vin)
        logger.info("已输入 VIN")

        self.wait.until(EC.element_to_be_clickable(self.QUERY_BUTTON)).click()
        logger.info("已点击查询，等待 %d 秒渲染结果...", QUERY_WAIT)
        time.sleep(QUERY_WAIT)

    def contains(self, keyword: str) -> bool:
        """
        在页面可见文本里精确搜索关键词：
        - 忽略大小写
        - 前后不能紧跟字母/数字/下划线（避免 HVSM_FLSeatTemp 匹配到 HVSM_FLSeatTempVD）
        """
        keyword = keyword.strip()
        if not keyword:
            return False

        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            body_text = self.driver.page_source

        pattern = re.compile(
            r"(?<![A-Za-z0-9_])" + re.escape(keyword) + r"(?![A-Za-z0-9_])",
            re.IGNORECASE,
        )
        return bool(pattern.search(body_text))