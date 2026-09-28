import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from config import LOGIN_URL, CAPTCHA_MAX_RETRY
from utils.captcha import recognize

logger = logging.getLogger(__name__)


class LoginPage:
    """中东运维管理系统 登录页"""

    USERNAME_INPUT = (By.CSS_SELECTOR, "input[placeholder='账号']")
    PASSWORD_INPUT = (By.CSS_SELECTOR, "input[placeholder='密码']")
    CAPTCHA_INPUT  = (By.CSS_SELECTOR, "input[placeholder='验证码']")
    CAPTCHA_IMG    = (By.CSS_SELECTOR, "img.login-code-img")
    LOGIN_BUTTON   = (By.XPATH, "//button[.//span[normalize-space()='登 录']]")
    LOGIN_FORM     = (By.CSS_SELECTOR, "form.login-form")

    def __init__(self, driver, wait: int = 15):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait)
        
        
    def login(self, username: str, password: str) -> None:
        self.driver.get(LOGIN_URL)
        self.wait.until(EC.presence_of_element_located(self.LOGIN_FORM))
    
        for attempt in range(1, CAPTCHA_MAX_RETRY + 1):
            logger.info("========== 登录尝试 %d / %d ==========", attempt, CAPTCHA_MAX_RETRY)
    
            self._fill(self.USERNAME_INPUT, username)
            self._fill(self.PASSWORD_INPUT, password)
    
            captcha_img = self.wait.until(EC.visibility_of_element_located(self.CAPTCHA_IMG))
            code = recognize(captcha_img)
            logger.info("识别答案: %r", code)
    
            self._fill(self.CAPTCHA_INPUT, code)
    
            self.wait.until(EC.element_to_be_clickable(self.LOGIN_BUTTON)).click()
    
            if self._is_login_success():
                logger.info("✅ 登录成功")
                return
    
            logger.warning("❌ 登录失败，刷新验证码重试")
            self._refresh_captcha()
            time.sleep(0.8)
    
        raise RuntimeError(f"验证码重试 {CAPTCHA_MAX_RETRY} 次仍登录失败")
    
    
    def _fill(self, locator, text: str, max_retry: int = 3) -> None:
        """稳定地填充 Element UI 输入框：JS 聚焦 + JS 清空 + 输入 + 校验 + 重试"""
        elem = None
        for attempt in range(1, max_retry + 1):
            elem = self.wait.until(EC.presence_of_element_located(locator))
    
            # 1. JS 聚焦，避免点击时命中前缀图标
            self.driver.execute_script("arguments[0].focus();", elem)
    
            # 2. JS 清空并触发 input 事件，让 Vue 感知
            self.driver.execute_script("""
                var el = arguments[0];
                var setter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value').set;
                setter.call(el, '');
                el.dispatchEvent(new Event('input', {bubbles: true}));
            """, elem)
    
            # 3. 输入
            elem.send_keys(text)
    
            # 4. 校验是否真的输进去了
            actual = elem.get_attribute("value")
            if actual == text:
                return
    
            logger.warning(
                "输入未生效，第 %d 次重试：期望 %r，实际 %r", attempt, text, actual
            )
            time.sleep(0.3)
    
            raise RuntimeError(
                f"输入框填充失败：期望 {text!r}，实际 {elem.get_attribute('value')!r}"
            )

    def _is_login_success(self) -> bool:
        try:
            WebDriverWait(self.driver, 5).until(
                EC.invisibility_of_element_located(self.LOGIN_FORM)
            )
            return True
        except TimeoutException:
            return False

    def _refresh_captcha(self) -> None:
        """强制刷新验证码：优先点图片，点不到就整页刷新"""
        try:
            img = self.driver.find_element(*self.CAPTCHA_IMG)
            old_src = img.get_attribute("src") or ""
            img.click()
            # 等 src 变化，确认刷新成功
            for _ in range(10):
                try:
                    new_src = self.driver.find_element(*self.CAPTCHA_IMG).get_attribute("src") or ""
                    if new_src != old_src:
                        return
                except Exception:
                    pass
                time.sleep(0.1)
            # 10 次没变，整页刷新
            self.driver.refresh()
            self.wait.until(EC.presence_of_element_located(self.LOGIN_FORM))
        except Exception:
            self.driver.refresh()
            self.wait.until(EC.presence_of_element_located(self.LOGIN_FORM))