import pyotp
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

CONED_LOGIN_URL = "https://www.coned.com/en/login"
CONED_USAGE_URL = (
    "https://www.coned.com/en/accounts-billing/dashboard?tab1=billingandusage-1"
)

DEFAULT_TIMEOUT_SEC = 10


class LoginFailedException(Exception):
    pass


class Coned:
    def __init__(self, user, password, totp, account_id, meter, maid=""):
        self.user = user
        self.password = password
        self.totp = totp
        self.account_id = account_id
        self.meter = meter
        self.maid = maid

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        self.driver = webdriver.Chrome(chrome_options=options)

    def opower_usage_url(self):
        return f"https://cned.opower.com/ei/edge/apis/cws-real-time-ami-v1/cws/cned/accounts/{self.account_id}/meters/{self.meter}/usage"  # noqa

    def login(self):
        # Try to load the Billing and Usage page. If we find ourselves at the
        # login page, then we need to login. If not, we have nothing to do.
        self.driver.get(CONED_USAGE_URL)
        if not self.at_login_page():
            return

        # Submit the login form
        self.driver.find_element_by_id("form-login-email").send_keys(self.user)
        self.driver.find_element_by_id("form-login-password").send_keys(self.password)
        self.driver.find_element_by_id("form-login-password").submit()

        # Wait for login form to get to 2FA step.
        try:
            tfa_field = WebDriverWait(self.driver, DEFAULT_TIMEOUT_SEC).until(
                EC.element_to_be_clickable((By.ID, "form-login-mfa-code"))
            )
        except TimeoutException as e:
            # If it times out, it's probably due to bad credentials.
            if self.is_bad_login():
                raise LoginFailedException
            else:
                raise e

        # Submit 2FA form
        totp = pyotp.TOTP(self.totp)
        tfa_field.send_keys(totp.now())
        tfa_field.submit()

        # Wait for dashboard to appear
        WebDriverWait(self.driver, DEFAULT_TIMEOUT_SEC).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-value='overview']"))
        )

        # If prompted to select service address, use maid id to resolve
        try:
            must_select = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class, 'account-focus__accounts-container')]")
                )
            )
            account_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//button[@data-maid='{self.maid}']")
                )
            )
            account_button.click()
        except TimeoutException:
            pass

    def get_usage(self):
        self.driver.get(CONED_USAGE_URL)

        # Go to "real time usage"
        rtu_button = WebDriverWait(self.driver, DEFAULT_TIMEOUT_SEC).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[@data-value='sectionRealTimeData']")
            )
        )
        rtu_button.click()

        # Wait for "Download your real-time usage" in the iframe to appear so
        # that it triggers authentication on the opower side
        iframe = WebDriverWait(self.driver, DEFAULT_TIMEOUT_SEC).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[@id='sectionRealTimeData']/iframe")
            )
        )
        self.driver.switch_to.frame(iframe)
        WebDriverWait(self.driver, DEFAULT_TIMEOUT_SEC).until(
            EC.element_to_be_clickable((By.ID, "download-link"))
        )

        # Get the usage from opower
        self.driver.get(self.opower_usage_url())
        return self.driver.find_element_by_tag_name("body").text

    def save_screenshot(self, filename):
        '''
        Saves a 1080p screenshot of the page with the given filename in
        the screenshots folder. Doesn't reset the window size.
        '''
        path = f"screenshots/{filename}.png"
        self.driver.set_window_size(1920, 1080)
        self.driver.save_screenshot(path)

    def at_login_page(self):
        '''
        at_login_page returns whether the driver is at the ConEd login
        page by looking for the login form.
        '''
        try:
            self.driver.find_element_by_id("form-login-email")
            return True
        except NoSuchElementException:
            return False

    def is_bad_login(self):
        '''
        is_bad_login returns whether there is a failed login indicator
        on the page.
        '''
        bad_login = self.driver.find_element_by_class_name("login-form__container-error")
        return 'you entered does not match our records' in bad_login.text
